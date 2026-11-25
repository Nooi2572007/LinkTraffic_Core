import re
import json
import urllib.request
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.core import signing
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from .models import Admin, User

# ==========================================
# 定数・共通ヘルパー関数
# ==========================================
MAX_LOGIN_ATTEMPTS = 6
LOCK_CONTACT_PHONE = '0120-000-000'  # ロックモーダル表示用問い合わせ窓口
PASSWORD_RESET_SALT = 'linktraffic-password-reset'
PASSWORD_RESET_MAX_AGE = 1800  # トークン有効期限（30分）


def render_account(request, template_name, context=None):
    """
    account/templates/account/〇〇.html と
    account/templates/〇〇.html のどちらに配置されていても読み込む
    """
    return render(request, [f'account/{template_name}', template_name], context)


def get_current_user(request):
    """セッションからログイン中の利用者(User)を取得"""
    user_id = request.session.get('user_id')
    if not user_id:
        return None
    return User.objects.filter(pk=user_id).exclude(user_status='none').first()


def get_current_admin(request):
    """セッションからログイン中の管理者(Admin)を取得"""
    admin_id = request.session.get('admin_id')
    if not admin_id:
        return None
    return Admin.objects.filter(pk=admin_id).first()


def user_login_required(view_func):
    """利用者ログイン必須デコレータ（管理者の代理操作も許可）"""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not get_current_user(request) and not get_current_admin(request):
            messages.warning(request, 'ログインが必要です。')
            return redirect('account:login')
        return view_func(request, *args, **kwargs)
    return _wrapped


def admin_login_required(view_func):
    """管理者ログイン必須デコレータ"""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not get_current_admin(request):
            messages.warning(request, '管理者としてログインしてください。')
            return redirect('account:login')
        return view_func(request, *args, **kwargs)
    return _wrapped


def _extract_account_form_data(post_data):
    """画面設計書間のname属性表記ゆれを吸収して辞書に正規化"""
    email = (post_data.get('email') or '').strip()
    password = post_data.get('password') or ''
    phone = (
        post_data.get('phone_number')
        or post_data.get('phone')
        or post_data.get('tel')
        or ''
    ).strip()
    post_code = (
        post_data.get('post_code')
        or post_data.get('zipcode')
        or post_data.get('zip_code')
        or ''
    ).strip()
    address = (post_data.get('address') or '').strip()
    company_name = (
        post_data.get('company_name')
        or post_data.get('company')
        or ''
    ).strip()
    industry = (post_data.get('industry') or '').strip()

    return {
        # モデル基準キー
        'email': email,
        'password': password,
        'phone_number': phone,
        'post_code': post_code,
        'address': address,
        'company_name': company_name,
        'industry': industry,
        # テンプレート互換用エイリアス
        'phone': phone,
        'tel': phone,
        'zipcode': post_code,
        'zip_code': post_code,
        'company': company_name,
    }


def _validate_account_data(data, is_update=False, exclude_user_id=None):
    """アカウント登録・変更共通の入力バリデーション"""
    errors = []

    # 1. メールアドレス
    if not data['email']:
        errors.append('メールアドレスが入力されていません。')
    elif len(data['email']) > 255:
        errors.append('メールアドレスは255文字以内で入力してください。')
    else:
        try:
            validate_email(data['email'])
            qs = User.objects.filter(email=data['email']).exclude(user_status='none')
            if exclude_user_id:
                qs = qs.exclude(pk=exclude_user_id)
            if qs.exists():
                errors.append('このメールアドレスは既に登録されています。')
        except ValidationError:
            errors.append('メールアドレスの形式が正しくありません。')

    # 2. パスワード（新規時は必須、変更時は入力時のみ検証）
    pwd = data['password']
    if not is_update and not pwd:
        errors.append('パスワードが入力されていません。')
    if pwd:
        if not (8 <= len(pwd) <= 64):
            errors.append('パスワードは8文字以上64文字以内で入力してください。')
        elif not re.search(r'[A-Za-z]', pwd) or not re.search(r'\d', pwd):
            errors.append('パスワードは英字と数字の両方を含めてください。')

    # 3. 電話番号（必須・数値のみ）
    if not data['phone_number']:
        errors.append('電話番号が入力されていません。')
    elif not re.fullmatch(r'\d{10,11}', data['phone_number']):
        errors.append('電話番号はハイフンなしの10桁〜11桁の数値で入力してください。')

    # 4. 郵便番号（必須・7桁数値）
    if not data['post_code']:
        errors.append('郵便番号が入力されていません。')
    elif not re.fullmatch(r'\d{7}', data['post_code']):
        errors.append('郵便番号はハイフンなしの7桁の数値で入力してください。')

    # 5. 住所
    if not data['address']:
        errors.append('住所が入力されていません。')

    # 6. 会社名（必須・重複チェック）
    if not data['company_name']:
        errors.append('会社名が入力されていません。')
    else:
        c_qs = User.objects.filter(company_name=data['company_name']).exclude(user_status='none')
        if exclude_user_id:
            c_qs = c_qs.exclude(pk=exclude_user_id)
        if c_qs.exists():
            errors.append('この会社名は既に登録されています。')

    # 7. 業種
    if not data['industry']:
        errors.append('業種が選択されていません。')

    return errors


# ==========================================
# 1. トップ・メイン・マイページ
# ==========================================
def top_view(request):
    """トップ画面（未ログイン時の入口）"""
    if get_current_user(request):
        return redirect('account:main')
    if get_current_admin(request):
        return redirect('account:admin')
    return render_account(request, 'top.html')


@user_login_required
def main_view(request):
    """メイン画面（ログイン後の利用者ホーム）"""
    user = get_current_user(request)
    if not user and get_current_admin(request):
        return redirect('account:admin')

    subsc = getattr(user, 'subsc', None)
    is_subscribed = bool(subsc and getattr(subsc, 'status', '') == 'active')

    context = {
        'user': user,
        'is_subscribed': is_subscribed,
        'subsc': subsc,
    }
    return render_account(request, 'main.html', context)


@user_login_required
def mypage_view(request):
    """マイページ画面"""
    user = get_current_user(request)
    if not user:
        return redirect('account:admin')

    subsc = getattr(user, 'subsc', None)
    context = {
        'user': user,
        'subsc': subsc,
        'last_login': request.session.get('last_login_str', '初回ログイン'),
    }
    return render_account(request, 'mypage.html', context)


# ==========================================
# 2. ログイン・アカウントロック・ログアウト
# ==========================================
def login_view(request):
    """
    ログイン画面 & アカウントロック処理
    - 連続6回失敗でアカウントステータスを 'look'（ロック）に変更
    - ロック済みアカウントはモーダル表示用フラグを返却
    """
    context = {
        'email': '',
        'is_locked': False,
        'lock_phone': LOCK_CONTACT_PHONE,
    }

    if request.method == 'POST':
        email = (request.POST.get('email') or '').strip()
        password = request.POST.get('password') or ''
        context['email'] = email

        # 3a. 形式・必須チェック
        if not email or not password or len(email) > 255 or not (8 <= len(password) <= 64):
            messages.error(request, '入力内容を確認してください。')
            return render_account(request, 'login.html', context)

        # 管理者アカウントの認証チェック
        admin_obj = Admin.objects.filter(email=email).first()
        if admin_obj:
            is_valid_admin = (
                check_password(password, admin_obj.password)
                if admin_obj.password.startswith(('pbkdf2_', 'argon2$', 'bcrypt'))
                else (password == admin_obj.password)
            )
            if is_valid_admin:
                request.session.flush()
                request.session['admin_id'] = admin_obj.pk
                request.session['admin_name'] = getattr(admin_obj, 'name', email)
                request.session['last_login_str'] = timezone.localtime().strftime('%Y/%m/%d %H:%M')
                return redirect('account:admin')
            else:
                messages.error(request, 'ユーザーIDまたはパスワードが正しくありません。')
                return render_account(request, 'login.html', context)

        # 利用者アカウントの検索（論理削除済み 'none' は除外）
        user = User.objects.filter(email=email).exclude(user_status='none').first()
        if not user:
            messages.error(request, 'ユーザーIDまたはパスワードが正しくありません。')
            return render_account(request, 'login.html', context)

        # 既にロック状態（'look' または 'lock'）か判定
        if user.user_status in ('look', 'lock'):
            context['is_locked'] = True
            context['lock_message'] = (
                f'このアカウントはロックされています。解除については下記の電話番号にお掛けください。\n{LOCK_CONTACT_PHONE}'
            )
            return render_account(request, 'login.html', context)

        # パスワード照合（ハッシュ化済み・平文の両方に対応）
        is_valid = (
            check_password(password, user.password)
            if user.password.startswith(('pbkdf2_', 'argon2$', 'bcrypt'))
            else (password == user.password)
        )

        # 失敗回数の管理（モデルにフィールドがあればDB優先、なければセッション管理）
        fail_session_key = f'login_fail_count_{user.pk}'
        current_fails = (
            getattr(user, 'failed_login_count', None)
            if hasattr(user, 'failed_login_count')
            else request.session.get(fail_session_key, 0)
        )

        if is_valid:
            # 認証成功：連続失敗回数を0にリセットしてセッション開始
            if hasattr(user, 'failed_login_count'):
                user.failed_login_count = 0
            if hasattr(user, 'last_login'):
                user.last_login = timezone.now()
            user.save()

            request.session.flush()
            request.session['user_id'] = user.pk
            request.session['company_name'] = user.company_name
            request.session['last_login_str'] = timezone.localtime().strftime('%Y/%m/%d %H:%M')
            return redirect('account:main')
        else:
            # 認証失敗：連続失敗回数を +1
            current_fails += 1
            if hasattr(user, 'failed_login_count'):
                user.failed_login_count = current_fails

            if current_fails >= MAX_LOGIN_ATTEMPTS:
                # 6回に達した場合：ステータスをロックに変更しロック日時を記録
                user.user_status = 'look'
                if hasattr(user, 'locked_at'):
                    user.locked_at = timezone.now()
                user.save()
                if fail_session_key in request.session:
                    del request.session[fail_session_key]

                context['is_locked'] = True
                context['lock_message'] = (
                    f'このアカウントはロックされています。解除については下記の電話番号にお掛けください。\n{LOCK_CONTACT_PHONE}'
                )
                return render_account(request, 'login.html', context)
            else:
                if hasattr(user, 'failed_login_count'):
                    user.save()
                else:
                    request.session[fail_session_key] = current_fails
                messages.error(request, 'ユーザーIDまたはパスワードが正しくありません。')
                return render_account(request, 'login.html', context)

    return render_account(request, 'login.html', context)


def logout_view(request):
    """ログアウト処理"""
    request.session.flush()
    messages.info(request, 'ログアウトしました。')
    return redirect('account:top')


# ==========================================
# 3. アカウント新規登録（入力 -> 確認 -> 完了）
# ==========================================
def user_register_view(request):
    """アカウント新規登録画面"""
    session_key = 'register_form_data'

    if request.method == 'POST':
        data = _extract_account_form_data(request.POST)
        errors = _validate_account_data(data, is_update=False)

        if errors:
            for err in errors:
                messages.error(request, err)
            return render_account(request, 'user_register.html', {'form_data': data})

        request.session[session_key] = data
        return redirect('account:user_register_confirm')

    form_data = request.session.get(session_key, {})
    return render_account(request, 'user_register.html', {'form_data': form_data})


def user_register_confirm_view(request):
    """アカウント新規登録確認画面"""
    session_key = 'register_form_data'
    data = request.session.get(session_key)
    if not data:
        return redirect('account:user_register')

    if request.method == 'POST':
        # 「修正する」ボタン押下時
        if 'return_btn' in request.POST:
            return redirect('account:user_register')

        # 「登録する」ボタン押下時
        errors = _validate_account_data(data, is_update=False)
        if errors:
            for err in errors:
                messages.error(request, err)
            return redirect('account:user_register')

        user = User.objects.create(
            email=data['email'],
            password=make_password(data['password']),
            phone_number=data['phone_number'],
            post_code=data['post_code'],
            address=data['address'],
            company_name=data['company_name'],
            industry=data['industry'],
            user_status='active',
        )

        del request.session[session_key]
        request.session['user_id'] = user.pk
        request.session['company_name'] = user.company_name
        request.session['last_login_str'] = timezone.localtime().strftime('%Y/%m/%d %H:%M')
        return redirect('account:user_register_done')

    context = {
        'form_data': data,
        'masked_password': '●' * len(data.get('password', '')),
    }
    return render_account(request, 'user_register_confirm.html', context)


def user_register_done_view(request):
    """アカウント新規登録完了画面"""
    user = get_current_user(request)
    return render_account(request, 'user_register_done.html', {'user': user})


# ==========================================
# 4. アカウント変更（入力 -> 確認 -> 完了）
# ==========================================
def _resolve_target_user(request):
    """操作対象のUserを解決（利用者本人、または管理者が選択中の対象会員）"""
    user = get_current_user(request)
    if user:
        return user, False

    admin = get_current_admin(request)
    if admin:
        target_id = request.GET.get('user_id') or request.POST.get('user_id') or request.session.get('admin_target_user_id')
        if target_id:
            target_user = User.objects.filter(pk=target_id).exclude(user_status='none').first()
            if target_user:
                request.session['admin_target_user_id'] = target_user.pk
                return target_user, True
    return None, False


@user_login_required
def user_update_view(request):
    """アカウント変更画面"""
    target_user, is_admin_mode = _resolve_target_user(request)
    if not target_user:
        messages.error(request, '対象のアカウント情報が見つかりません。')
        return redirect('account:admin_user_list' if get_current_admin(request) else 'account:login')

    session_key = f'update_form_data_{target_user.pk}'

    if request.method == 'POST':
        data = _extract_account_form_data(request.POST)
        errors = _validate_account_data(data, is_update=True, exclude_user_id=target_user.pk)

        if errors:
            for err in errors:
                messages.error(request, err)
            return render_account(request, 'user_update.html', {
                'user': target_user,
                'form_data': data,
                'is_admin_mode': is_admin_mode,
            })

        request.session[session_key] = data
        return redirect('account:user_update_confirm')

    saved_data = request.session.get(session_key)
    if saved_data:
        form_data = saved_data
    else:
        form_data = {
            'email': target_user.email,
            'password': '',
            'phone_number': target_user.phone_number,
            'phone': target_user.phone_number,
            'tel': target_user.phone_number,
            'post_code': target_user.post_code,
            'zipcode': target_user.post_code,
            'zip_code': target_user.post_code,
            'address': target_user.address,
            'company_name': target_user.company_name,
            'company': target_user.company_name,
            'industry': target_user.industry,
        }

    return render_account(request, 'user_update.html', {
        'user': target_user,
        'form_data': form_data,
        'is_admin_mode': is_admin_mode,
    })


@user_login_required
def user_update_confirm_view(request):
    """アカウント変更確認画面"""
    target_user, is_admin_mode = _resolve_target_user(request)
    if not target_user:
        return redirect('account:login')

    session_key = f'update_form_data_{target_user.pk}'
    data = request.session.get(session_key)
    if not data:
        return redirect('account:user_update')

    if request.method == 'POST':
        if 'return_btn' in request.POST:
            return redirect('account:user_update')

        errors = _validate_account_data(data, is_update=True, exclude_user_id=target_user.pk)
        if errors:
            for err in errors:
                messages.error(request, err)
            return redirect('account:user_update')

        target_user.email = data['email']
        if data['password']:
            target_user.password = make_password(data['password'])
        target_user.phone_number = data['phone_number']
        target_user.post_code = data['post_code']
        target_user.address = data['address']
        target_user.company_name = data['company_name']
        target_user.industry = data['industry']
        target_user.save()

        del request.session[session_key]
        if not is_admin_mode:
            request.session['company_name'] = target_user.company_name
        return redirect('account:user_update_done')

    context = {
        'user': target_user,
        'form_data': data,
        'password_display': ('●' * len(data['password'])) if data['password'] else '（変更なし）',
        'is_admin_mode': is_admin_mode,
    }
    return render_account(request, 'user_update_confirm.html', context)


@user_login_required
def user_update_done_view(request):
    """アカウント変更完了画面"""
    target_user, is_admin_mode = _resolve_target_user(request)
    return render_account(request, 'user_update_done.html', {
        'user': target_user,
        'is_admin_mode': is_admin_mode,
    })


# ==========================================
# 5. アカウント削除（確認 -> 完了）
# ==========================================
@user_login_required
def user_archive_view(request):
    """
    アカウント削除確認画面
    - サブスク更新停止処理を実行後、アカウントを論理削除（user_status='none'）
    - 利用者本人の場合はセッションを破棄してログアウト
    """
    target_user, is_admin_mode = _resolve_target_user(request)
    if not target_user:
        messages.error(request, '対象のアカウント情報が見つかりません。')
        return redirect('account:admin_user_list' if get_current_admin(request) else 'account:login')

    if request.method == 'POST':
        if 'cancel_btn' in request.POST:
            if is_admin_mode:
                return redirect('account:admin_user_details', user_id=target_user.pk)
            return redirect('account:mypage')

        subsc = getattr(target_user, 'subsc', None)
        if subsc:
            if hasattr(subsc, 'status'):
                subsc.status = 'canceled'
            if hasattr(subsc, 'auto_renew'):
                subsc.auto_renew = False
            subsc.save()

        target_user.user_status = 'none'
        target_user.save()

        if is_admin_mode:
            request.session.pop('admin_target_user_id', None)
            messages.success(request, f'会員ID: {target_user.pk}（{target_user.company_name}）のアカウントを削除しました。')
            return redirect('account:admin_user_list')
        else:
            request.session.flush()
            return redirect('account:user_archive_done')

    return render_account(request, 'user_archive.html', {
        'user': target_user,
        'is_admin_mode': is_admin_mode,
    })


def user_archive_done_view(request):
    """アカウント削除完了画面"""
    return render_account(request, 'user_archive_done.html')


# ==========================================
# 6. パスワード再設定（リンク送信 -> 再設定 -> 完了）
# ==========================================
def password_reset_link_view(request):
    """パスワード再設定リンク送信画面"""
    if request.method == 'POST':
        email = (request.POST.get('email') or request.POST.get('submit') or '').strip()
        if not email:
            messages.error(request, 'メールアドレスを入力してください。')
            return render_account(request, 'password_reset_link.html')

        user = User.objects.filter(email=email).exclude(user_status='none').first()
        if user:
            token = signing.dumps({'user_id': user.pk, 'email': user.email}, salt=PASSWORD_RESET_SALT)
            reset_url = request.build_absolute_uri(
                reverse('account:password_reset', kwargs={'token': token})
            )

            send_mail(
                subject='【LinkTraffic】パスワード再設定のご案内',
                message=(
                    f'{user.company_name} 様\n\n'
                    '以下のURLより新しいパスワードを再設定してください（有効期限：30分）。\n'
                    f'{reset_url}\n'
                ),
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@linktraffic.example.com'),
                recipient_list=[user.email],
                fail_silently=True,
            )

        messages.success(request, 'ご入力いただいたメールアドレス宛にパスワード再設定用URLを送信しました。')
        return render_account(request, 'password_reset_link.html', {'sent': True})

    return render_account(request, 'password_reset_link.html')


def password_reset_view(request, token):
    """パスワード再設定画面"""
    try:
        payload = signing.loads(token, salt=PASSWORD_RESET_SALT, max_age=PASSWORD_RESET_MAX_AGE)
    except (signing.BadSignature, signing.SignatureExpired):
        messages.error(request, '再設定用URLが無効か、有効期限が切れています。もう一度お手続きください。')
        return redirect('account:password_reset_link')

    user = User.objects.filter(pk=payload.get('user_id'), email=payload.get('email')).exclude(user_status='none').first()
    if not user:
        messages.error(request, '対象のアカウントが見つかりません。')
        return redirect('account:password_reset_link')

    if request.method == 'POST':
        new_password = request.POST.get('new_password') or ''
        new_password_confirm = request.POST.get('new_password_confirm') or ''

        if not (8 <= len(new_password) <= 64):
            messages.error(request, '新しいパスワードは8文字以上64文字以内で入力してください。')
            return render_account(request, 'password_reset.html', {'token': token})

        if not re.search(r'[A-Za-z]', new_password) or not re.search(r'\d', new_password):
            messages.error(request, '新しいパスワードは英字と数字の両方を含めてください。')
            return render_account(request, 'password_reset.html', {'token': token})

        if new_password != new_password_confirm:
            messages.error(request, '新しいパスワードと確認用パスワードが一致しません。')
            return render_account(request, 'password_reset.html', {'token': token})

        user.password = make_password(new_password)
        user.save()
        return redirect('account:password_reset_done')

    return render_account(request, 'password_reset.html', {'token': token})


def password_reset_done_view(request):
    """パスワード再設定完了画面"""
    return render_account(request, 'password_reset_done.html')


# ==========================================
# 7. 郵便番号検索API（住所自動入力用）
# ==========================================
def zipcode_search_api(request):
    """郵便番号（7桁）から住所を取得してJSONで返却"""
    zipcode = re.sub(r'\D', '', request.GET.get('zipcode') or request.GET.get('zip_code') or '')
    if len(zipcode) != 7:
        return JsonResponse({'success': False, 'message': '郵便番号は7桁の数値で入力してください。'}, status=400)

    try:
        url = f'https://zipcloud.ibsnet.co.jp/api/search?zipcode={zipcode}'
        with urllib.request.urlopen(url, timeout=5) as res:
            body = json.loads(res.read().decode('utf-8'))
        if body.get('results'):
            item = body['results'][0]
            full_address = f"{item['address1']}{item['address2']}{item['address3']}"
            return JsonResponse({'success': True, 'address': full_address})
        return JsonResponse({'success': False, 'message': '該当する住所が見つかりませんでした。'}, status=404)
    except Exception:
        return JsonResponse({'success': False, 'message': '住所検索に失敗しました。手動で入力してください。'}, status=500)


# ==========================================
# 8. 管理者向けアカウント管理（ダッシュボード・一覧・詳細・ロック解除）
# ==========================================
@admin_login_required
def admin_dashboard_view(request):
    """管理者画面"""
    admin = get_current_admin(request)
    active_user_count = User.objects.filter(user_status='active').count()
    context = {
        'admin': admin,
        'active_user_count': active_user_count,
        'last_login': request.session.get('last_login_str', ''),
    }
    return render_account(request, 'admin.html', context)


@admin_login_required
def admin_user_list_view(request):
    """アカウント一覧画面（検索・選択対応）"""
    admin = get_current_admin(request)
    keyword = (request.GET.get('q') or request.GET.get('keyword') or '').strip()

    users = User.objects.exclude(user_status='none').order_by('pk')
    if keyword:
        query = Q(company_name__icontains=keyword) | Q(email__icontains=keyword)
        if keyword.isdigit():
            query |= Q(pk=int(keyword))
        users = users.filter(query)

    if request.method == 'POST':
        selected_id = request.POST.get('account_id')
        if not selected_id:
            messages.error(request, '対象のアカウントを選択してください。')
        else:
            return redirect('account:admin_user_details', user_id=int(selected_id))

    context = {
        'admin': admin,
        'users': users,
        'keyword': keyword,
    }
    return render_account(request, 'admin_user_list.html', context)


@admin_login_required
def admin_user_details_view(request, user_id):
    """アカウント詳細画面 & アカウントロック解除処理"""
    admin = get_current_admin(request)
    target_user = User.objects.filter(pk=user_id).exclude(user_status='none').first()

    if not target_user:
        messages.error(request, '対象のアカウント情報が見つかりません。')
        return redirect('account:admin_user_list')

    request.session['admin_target_user_id'] = target_user.pk

    if request.method == 'POST':
        if 'unlock_user' in request.POST:
            target_user.user_status = 'active'
            if hasattr(target_user, 'failed_login_count'):
                target_user.failed_login_count = 0
            if hasattr(target_user, 'locked_at'):
                target_user.locked_at = None
            target_user.save()
            messages.success(request, f'{target_user.company_name} のアカウントロックを解除しました。')
            return redirect('account:admin_user_details', user_id=target_user.pk)

    subsc = getattr(target_user, 'subsc', None)
    context = {
        'admin': admin,
        'target_user': target_user,
        'subsc': subsc,
        'is_locked': target_user.user_status in ('look', 'lock'),
    }
    return render_account(request, 'admin_user_details.html', context)