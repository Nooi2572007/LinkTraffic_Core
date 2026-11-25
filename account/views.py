import json
import re
import urllib.request

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
from django.views import View

from .models import Admin, User

# ==========================================
# 定数定義
# ==========================================
MAX_LOGIN_ATTEMPTS = 6
LOCK_CONTACT_PHONE = '0120-000-000'
PASSWORD_RESET_SALT = 'linktraffic-password-reset'
PASSWORD_RESET_MAX_AGE = 1800  # 30分


# ==========================================
# 共通ミックスイン（基底クラス用補助機能）
# ==========================================
class AccountBaseMixin:
    """テンプレート描画・セッション取得の共通処理"""
    template_name = ''
    fallback_templates = []

    def get_template_names(self):
        names = []
        if self.template_name:
            names.extend([f'account/{self.template_name}', self.template_name])
        names.extend(self.fallback_templates)
        return names

    def render_page(self, request, context=None):
        return render(request, self.get_template_names(), context or {})

    def get_current_user(self, request):
        user_id = request.session.get('user_id')
        if not user_id:
            return None
        return User.objects.filter(pk=user_id).exclude(user_status='none').first()

    def get_current_admin(self, request):
        admin_id = request.session.get('admin_id')
        if not admin_id:
            return None
        return Admin.objects.filter(pk=admin_id).first()


class UserLoginRequiredMixin(AccountBaseMixin):
    """利用者ログイン必須（管理者の代理操作も許可）"""
    def dispatch(self, request, *args, **kwargs):
        if not self.get_current_user(request) and not self.get_current_admin(request):
            messages.warning(request, 'ログインが必要です。')
            return redirect('account:login')
        return super().dispatch(request, *args, **kwargs)


class AdminLoginRequiredMixin(AccountBaseMixin):
    """管理者ログイン必須"""
    def dispatch(self, request, *args, **kwargs):
        if not self.get_current_admin(request):
            messages.warning(request, '管理者としてログインしてください。')
            return redirect('account:login')
        return super().dispatch(request, *args, **kwargs)


class AccountFormMixin(AccountBaseMixin):
    """アカウント登録・変更フォームの正規化・バリデーション"""
    def extract_form_data(self, post_data):
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

    def validate_account_data(self, data, is_update=False, exclude_user_id=None):
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

        # 2. パスワード
        pwd = data['password']
        if not is_update and not pwd:
            errors.append('パスワードが入力されていません。')
        if pwd:
            if not (8 <= len(pwd) <= 64):
                errors.append('パスワードは8文字以上64文字以内で入力してください。')
            elif not re.search(r'[A-Za-z]', pwd) or not re.search(r'\d', pwd):
                errors.append('パスワードは英字と数字の両方を含めてください。')

        # 3. 電話番号
        if not data['phone_number']:
            errors.append('電話番号が入力されていません。')
        elif not re.fullmatch(r'\d{10,11}', data['phone_number']):
            errors.append('電話番号はハイフンなしの10桁〜11桁の数値で入力してください。')

        # 4. 郵便番号
        if not data['post_code']:
            errors.append('郵便番号が入力されていません。')
        elif not re.fullmatch(r'\d{7}', data['post_code']):
            errors.append('郵便番号はハイフンなしの7桁の数値で入力してください。')

        # 5. 住所
        if not data['address']:
            errors.append('住所が入力されていません。')

        # 6. 会社名
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

    def resolve_target_user(self, request):
        user = self.get_current_user(request)
        if user:
            return user, False

        admin = self.get_current_admin(request)
        if admin:
            target_id = (
                request.GET.get('user_id')
                or request.POST.get('user_id')
                or request.session.get('admin_target_user_id')
            )
            if target_id:
                target_user = User.objects.filter(pk=target_id).exclude(user_status='none').first()
                if target_user:
                    request.session['admin_target_user_id'] = target_user.pk
                    return target_user, True
        return None, False


# ==========================================
# 1. トップ・メイン・マイページ
# ==========================================
class TopView(AccountBaseMixin, View):
    """トップ画面（top.html がなければ index.html を表示）"""
    template_name = 'top.html'
    fallback_templates = ['index.html']

    def get(self, request):
        if self.get_current_user(request):
            return redirect('account:main')
        if self.get_current_admin(request):
            return redirect('account:admin')
        return self.render_page(request)


class MainView(UserLoginRequiredMixin, View):
    """メイン画面（ログイン後の利用者ホーム）"""
    template_name = 'main.html'

    def get(self, request):
        user = self.get_current_user(request)
        if not user and self.get_current_admin(request):
            return redirect('account:admin')

        subsc = getattr(user, 'subsc', None)
        is_subscribed = bool(subsc and getattr(subsc, 'status', '') == 'active')

        return self.render_page(request, {
            'user': user,
            'is_subscribed': is_subscribed,
            'subsc': subsc,
        })


class MypageView(UserLoginRequiredMixin, View):
    """マイページ画面"""
    template_name = 'mypage.html'

    def get(self, request):
        user = self.get_current_user(request)
        if not user:
            return redirect('account:admin')

        subsc = getattr(user, 'subsc', None)
        return self.render_page(request, {
            'user': user,
            'subsc': subsc,
            'last_login': request.session.get('last_login_str', '初回ログイン'),
        })


# ==========================================
# 2. ログイン・アカウントロック・ログアウト
# ==========================================
class LoginView(AccountBaseMixin, View):
    """ログイン画面 & アカウントロック処理"""
    template_name = 'login.html'

    def get(self, request):
        return self.render_page(request, {
            'email': '',
            'is_locked': False,
            'lock_phone': LOCK_CONTACT_PHONE,
        })

    def post(self, request):
        email = (request.POST.get('email') or '').strip()
        password = request.POST.get('password') or ''
        context = {
            'email': email,
            'is_locked': False,
            'lock_phone': LOCK_CONTACT_PHONE,
        }

        if not email or not password or len(email) > 255 or not (8 <= len(password) <= 64):
            messages.error(request, '入力内容を確認してください。')
            return self.render_page(request, context)

        # 管理者認証
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
            messages.error(request, 'ユーザーIDまたはパスワードが正しくありません。')
            return self.render_page(request, context)

        # 利用者認証
        user = User.objects.filter(email=email).exclude(user_status='none').first()
        if not user:
            messages.error(request, 'ユーザーIDまたはパスワードが正しくありません。')
            return self.render_page(request, context)

        if user.user_status in ('look', 'lock'):
            context['is_locked'] = True
            context['lock_message'] = (
                f'このアカウントはロックされています。解除については下記の電話番号にお掛けください。\n{LOCK_CONTACT_PHONE}'
            )
            return self.render_page(request, context)

        is_valid = (
            check_password(password, user.password)
            if user.password.startswith(('pbkdf2_', 'argon2$', 'bcrypt'))
            else (password == user.password)
        )

        fail_session_key = f'login_fail_count_{user.pk}'
        current_fails = (
            getattr(user, 'failed_login_count', None)
            if hasattr(user, 'failed_login_count')
            else request.session.get(fail_session_key, 0)
        )

        if is_valid:
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

        current_fails += 1
        if hasattr(user, 'failed_login_count'):
            user.failed_login_count = current_fails

        if current_fails >= MAX_LOGIN_ATTEMPTS:
            user.user_status = 'look'
            if hasattr(user, 'locked_at'):
                user.locked_at = timezone.now()
            user.save()
            request.session.pop(fail_session_key, None)

            context['is_locked'] = True
            context['lock_message'] = (
                f'このアカウントはロックされています。解除については下記の電話番号にお掛けください。\n{LOCK_CONTACT_PHONE}'
            )
            return self.render_page(request, context)

        if hasattr(user, 'failed_login_count'):
            user.save()
        else:
            request.session[fail_session_key] = current_fails
        messages.error(request, 'ユーザーIDまたはパスワードが正しくありません。')
        return self.render_page(request, context)


class LogoutView(View):
    """ログアウト処理"""
    def get(self, request):
        request.session.flush()
        messages.info(request, 'ログアウトしました。')
        return redirect('account:top')

    def post(self, request):
        return self.get(request)


# ==========================================
# 3. アカウント新規登録（入力 -> 確認 -> 完了）
# ==========================================
class UserRegisterView(AccountFormMixin, View):
    """アカウント新規登録画面"""
    template_name = 'user_register.html'
    session_key = 'register_form_data'

    def get(self, request):
        form_data = request.session.get(self.session_key, {})
        return self.render_page(request, {'form_data': form_data})

    def post(self, request):
        data = self.extract_form_data(request.POST)
        errors = self.validate_account_data(data, is_update=False)

        if errors:
            for err in errors:
                messages.error(request, err)
            return self.render_page(request, {'form_data': data})

        request.session[self.session_key] = data
        return redirect('account:user_register_confirm')


class UserRegisterConfirmView(AccountFormMixin, View):
    """アカウント新規登録確認画面"""
    template_name = 'user_register_confirm.html'
    session_key = 'register_form_data'

    def get(self, request):
        data = request.session.get(self.session_key)
        if not data:
            return redirect('account:user_register')

        return self.render_page(request, {
            'form_data': data,
            'masked_password': '●' * len(data.get('password', '')),
        })

    def post(self, request):
        data = request.session.get(self.session_key)
        if not data:
            return redirect('account:user_register')

        if 'return_btn' in request.POST:
            return redirect('account:user_register')

        errors = self.validate_account_data(data, is_update=False)
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

        del request.session[self.session_key]
        request.session['user_id'] = user.pk
        request.session['company_name'] = user.company_name
        request.session['last_login_str'] = timezone.localtime().strftime('%Y/%m/%d %H:%M')
        return redirect('account:user_register_done')


class UserRegisterDoneView(AccountBaseMixin, View):
    """アカウント新規登録完了画面"""
    template_name = 'user_register_done.html'

    def get(self, request):
        user = self.get_current_user(request)
        return self.render_page(request, {'user': user})


# ==========================================
# 4. アカウント変更（入力 -> 確認 -> 完了）
# ==========================================
class UserUpdateView(UserLoginRequiredMixin, AccountFormMixin, View):
    """アカウント変更画面"""
    template_name = 'user_update.html'

    def get(self, request):
        target_user, is_admin_mode = self.resolve_target_user(request)
        if not target_user:
            messages.error(request, '対象のアカウント情報が見つかりません。')
            return redirect('account:admin_user_list' if self.get_current_admin(request) else 'account:login')

        session_key = f'update_form_data_{target_user.pk}'
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

        return self.render_page(request, {
            'user': target_user,
            'form_data': form_data,
            'is_admin_mode': is_admin_mode,
        })

    def post(self, request):
        target_user, is_admin_mode = self.resolve_target_user(request)
        if not target_user:
            messages.error(request, '対象のアカウント情報が見つかりません。')
            return redirect('account:admin_user_list' if self.get_current_admin(request) else 'account:login')

        session_key = f'update_form_data_{target_user.pk}'
        data = self.extract_form_data(request.POST)
        errors = self.validate_account_data(data, is_update=True, exclude_user_id=target_user.pk)

        if errors:
            for err in errors:
                messages.error(request, err)
            return self.render_page(request, {
                'user': target_user,
                'form_data': data,
                'is_admin_mode': is_admin_mode,
            })

        request.session[session_key] = data
        return redirect('account:user_update_confirm')


class UserUpdateConfirmView(UserLoginRequiredMixin, AccountFormMixin, View):
    """アカウント変更確認画面"""
    template_name = 'user_update_confirm.html'

    def get(self, request):
        target_user, is_admin_mode = self.resolve_target_user(request)
        if not target_user:
            return redirect('account:login')

        session_key = f'update_form_data_{target_user.pk}'
        data = request.session.get(session_key)
        if not data:
            return redirect('account:user_update')

        return self.render_page(request, {
            'user': target_user,
            'form_data': data,
            'password_display': ('●' * len(data['password'])) if data['password'] else '（変更なし）',
            'is_admin_mode': is_admin_mode,
        })

    def post(self, request):
        target_user, is_admin_mode = self.resolve_target_user(request)
        if not target_user:
            return redirect('account:login')

        session_key = f'update_form_data_{target_user.pk}'
        data = request.session.get(session_key)
        if not data:
            return redirect('account:user_update')

        if 'return_btn' in request.POST:
            return redirect('account:user_update')

        errors = self.validate_account_data(data, is_update=True, exclude_user_id=target_user.pk)
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


class UserUpdateDoneView(UserLoginRequiredMixin, AccountFormMixin, View):
    """アカウント変更完了画面"""
    template_name = 'user_update_done.html'

    def get(self, request):
        target_user, is_admin_mode = self.resolve_target_user(request)
        return self.render_page(request, {
            'user': target_user,
            'is_admin_mode': is_admin_mode,
        })


# ==========================================
# 5. アカウント削除（確認 -> 完了）
# ==========================================
class UserArchiveView(UserLoginRequiredMixin, AccountFormMixin, View):
    """アカウント削除確認画面"""
    template_name = 'user_archive.html'

    def get(self, request):
        target_user, is_admin_mode = self.resolve_target_user(request)
        if not target_user:
            messages.error(request, '対象のアカウント情報が見つかりません。')
            return redirect('account:admin_user_list' if self.get_current_admin(request) else 'account:login')

        return self.render_page(request, {
            'user': target_user,
            'is_admin_mode': is_admin_mode,
        })

    def post(self, request):
        target_user, is_admin_mode = self.resolve_target_user(request)
        if not target_user:
            messages.error(request, '対象のアカウント情報が見つかりません。')
            return redirect('account:admin_user_list' if self.get_current_admin(request) else 'account:login')

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

        request.session.flush()
        return redirect('account:user_archive_done')


class UserArchiveDoneView(AccountBaseMixin, View):
    """アカウント削除完了画面"""
    template_name = 'user_archive_done.html'

    def get(self, request):
        return self.render_page(request)


# ==========================================
# 6. パスワード再設定（リンク送信 -> 再設定 -> 完了）
# ==========================================
class PasswordResetLinkView(AccountBaseMixin, View):
    """パスワード再設定リンク送信画面"""
    template_name = 'password_reset_link.html'

    def get(self, request):
        return self.render_page(request)

    def post(self, request):
        email = (request.POST.get('email') or request.POST.get('submit') or '').strip()
        if not email:
            messages.error(request, 'メールアドレスを入力してください。')
            return self.render_page(request)

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
        return self.render_page(request, {'sent': True})


class PasswordResetView(AccountBaseMixin, View):
    """パスワード再設定画面"""
    template_name = 'password_reset.html'

    def _get_valid_user(self, token):
        try:
            payload = signing.loads(token, salt=PASSWORD_RESET_SALT, max_age=PASSWORD_RESET_MAX_AGE)
        except (signing.BadSignature, signing.SignatureExpired):
            return None
        return User.objects.filter(
            pk=payload.get('user_id'),
            email=payload.get('email'),
        ).exclude(user_status='none').first()

    def get(self, request, token):
        user = self._get_valid_user(token)
        if not user:
            messages.error(request, '再設定用URLが無効か、有効期限が切れています。もう一度お手続きください。')
            return redirect('account:password_reset_link')
        return self.render_page(request, {'token': token})

    def post(self, request, token):
        user = self._get_valid_user(token)
        if not user:
            messages.error(request, '再設定用URLが無効か、有効期限が切れています。もう一度お手続きください。')
            return redirect('account:password_reset_link')

        new_password = request.POST.get('new_password') or ''
        new_password_confirm = request.POST.get('new_password_confirm') or ''

        if not (8 <= len(new_password) <= 64):
            messages.error(request, '新しいパスワードは8文字以上64文字以内で入力してください。')
            return self.render_page(request, {'token': token})

        if not re.search(r'[A-Za-z]', new_password) or not re.search(r'\d', new_password):
            messages.error(request, '新しいパスワードは英字と数字の両方を含めてください。')
            return self.render_page(request, {'token': token})

        if new_password != new_password_confirm:
            messages.error(request, '新しいパスワードと確認用パスワードが一致しません。')
            return self.render_page(request, {'token': token})

        user.password = make_password(new_password)
        user.save()
        return redirect('account:password_reset_done')


class PasswordResetDoneView(AccountBaseMixin, View):
    """パスワード再設定完了画面"""
    template_name = 'password_reset_done.html'

    def get(self, request):
        return self.render_page(request)


# ==========================================
# 7. 郵便番号検索API（住所自動入力用）
# ==========================================
class ZipcodeSearchApiView(View):
    """郵便番号（7桁）から住所を取得してJSONで返却"""
    def get(self, request):
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
# 8. 管理者向けアカウント管理
# ==========================================
class AdminDashboardView(AdminLoginRequiredMixin, View):
    """管理者画面"""
    template_name = 'admin.html'

    def get(self, request):
        admin = self.get_current_admin(request)
        active_user_count = User.objects.filter(user_status='active').count()
        return self.render_page(request, {
            'admin': admin,
            'active_user_count': active_user_count,
            'last_login': request.session.get('last_login_str', ''),
        })


class AdminUserListView(AdminLoginRequiredMixin, View):
    """アカウント一覧画面（検索・選択対応）"""
    template_name = 'admin_user_list.html'

    def _get_queryset(self, keyword):
        users = User.objects.exclude(user_status='none').order_by('pk')
        if keyword:
            query = Q(company_name__icontains=keyword) | Q(email__icontains=keyword)
            if keyword.isdigit():
                query |= Q(pk=int(keyword))
            users = users.filter(query)
        return users

    def get(self, request):
        admin = self.get_current_admin(request)
        keyword = (request.GET.get('q') or request.GET.get('keyword') or '').strip()
        return self.render_page(request, {
            'admin': admin,
            'users': self._get_queryset(keyword),
            'keyword': keyword,
        })

    def post(self, request):
        admin = self.get_current_admin(request)
        keyword = (request.GET.get('q') or request.GET.get('keyword') or '').strip()
        selected_id = request.POST.get('account_id')
        if not selected_id:
            messages.error(request, '対象のアカウントを選択してください。')
            return self.render_page(request, {
                'admin': admin,
                'users': self._get_queryset(keyword),
                'keyword': keyword,
            })
        return redirect('account:admin_user_details', user_id=int(selected_id))


class AdminUserDetailsView(AdminLoginRequiredMixin, View):
    """アカウント詳細画面 & アカウントロック解除処理"""
    template_name = 'admin_user_details.html'

    def get(self, request, user_id):
        admin = self.get_current_admin(request)
        target_user = User.objects.filter(pk=user_id).exclude(user_status='none').first()
        if not target_user:
            messages.error(request, '対象のアカウント情報が見つかりません。')
            return redirect('account:admin_user_list')

        request.session['admin_target_user_id'] = target_user.pk
        subsc = getattr(target_user, 'subsc', None)
        return self.render_page(request, {
            'admin': admin,
            'target_user': target_user,
            'subsc': subsc,
            'is_locked': target_user.user_status in ('look', 'lock'),
        })

    def post(self, request, user_id):
        target_user = User.objects.filter(pk=user_id).exclude(user_status='none').first()
        if not target_user:
            messages.error(request, '対象のアカウント情報が見つかりません。')
            return redirect('account:admin_user_list')

        if 'unlock_user' in request.POST:
            target_user.user_status = 'active'
            if hasattr(target_user, 'failed_login_count'):
                target_user.failed_login_count = 0
            if hasattr(target_user, 'locked_at'):
                target_user.locked_at = None
            target_user.save()
            messages.success(request, f'{target_user.company_name} のアカウントロックを解除しました。')

        return redirect('account:admin_user_details', user_id=target_user.pk)