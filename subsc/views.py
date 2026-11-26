import datetime
from dateutil.relativedelta import relativedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.core.paginator import Paginator
from .models import SubscPlan, Subsc, Payment, Credit, Bank


# ==========================================
# 1. サブスク登録 (Subsc Register)
# ==========================================
def subsc_register(request):
    plans = SubscPlan.objects.filter(status=True)
    link_id = request.session.get('link_id', 'dummy-link-uuid')

    if request.method == 'POST':
        plan_id = request.POST.get('plan_id')
        payment_method = request.POST.get('payment_method')  # 'credit' or 'bank'
        plan = get_object_or_404(SubscPlan, pk=plan_id)

        try:
            with transaction.atomic():
                credit_obj = None
                bank_obj = None

                if payment_method == 'credit':
                    credit_obj = Credit.objects.create(
                        link_id=link_id,
                        card_holder_name=request.POST.get('card_holder_name'),
                        last_card_number=request.POST.get('card_number')[-4:],
                        exp_month=int(request.POST.get('exp_month')),
                        exp_year=int(request.POST.get('exp_year')),
                    )
                elif payment_method == 'bank':
                    bank_obj = Bank.objects.create(
                        link_id=link_id,
                        bank_code=request.POST.get('bank_code'),
                        bank_name=request.POST.get('bank_name'),
                        bank_branch_code=request.POST.get('bank_branch_code'),
                        bank_branch_name=request.POST.get('bank_branch_name'),
                        bank_account_type=int(request.POST.get('bank_account_type', 1)),
                        bank_account_name_type=int(request.POST.get('bank_account_name_type', 1)),
                        bank_account_number=request.POST.get('bank_account_number'),
                        bank_account_holder_name=request.POST.get('bank_account_holder_name'),
                    )

                next_date = datetime.date.today() + relativedelta(months=plan.plan_interval)

                subsc = Subsc.objects.create(
                    link_id=link_id,
                    plan=plan,
                    subsc_status=Subsc.SubscStatus.ACTIVE,
                    next_subsc_date=next_date
                )

                Payment.objects.create(
                    subsc=subsc,
                    payment_method=payment_method,
                    credit_pay=credit_obj,
                    bankpay=bank_obj,
                    payment_status=Payment.PaymentStatus.PAID,
                    amount=plan.plan_price,
                    gateway_payment_id=f"gw_{timezone.now().strftime('%Y%m%d%H%M%S')}",
                    paid_at=timezone.now()
                )

            messages.success(request, 'サブスクリプションの登録が完了しました。')
            return redirect('subsc_update')

        except Exception as e:
            messages.error(request, f'登録中にエラーが発生しました: {str(e)}')

    return render(request, 'subsc_register.html', {'plans': plans})


# ==========================================
# 2. サブスク変更・解約 (Subsc Update / Cancel)
# ==========================================
def subsc_update(request):
    link_id = request.session.get('link_id', 'dummy-link-uuid')
    current_subsc = Subsc.objects.filter(link_id=link_id, subsc_status=Subsc.SubscStatus.ACTIVE).first()
    plans = SubscPlan.objects.filter(status=True)

    if request.method == 'POST' and current_subsc:
        new_plan_id = request.POST.get('plan_id')
        new_plan = get_object_or_404(SubscPlan, pk=new_plan_id)

        current_subsc.plan = new_plan
        current_subsc.updated_at = timezone.now()
        current_subsc.save()

        messages.success(request, 'サブスクリプションの内容を変更しました。')
        return redirect('subsc_update')

    return render(request, 'subsc_update.html', {
        'current_subsc': current_subsc,
        'plans': plans
    })


def subsc_cancel(request):
    if request.method == 'POST':
        link_id = request.session.get('link_id', 'dummy-link-uuid')
        current_subsc = get_object_or_404(Subsc, link_id=link_id, subsc_status=Subsc.SubscStatus.ACTIVE)
        current_subsc.subsc_status = Subsc.SubscStatus.UNSUBSCRIBE
        current_subsc.unsubscribed_at = timezone.now()
        current_subsc.save()
        messages.info(request, 'サブスクリプションを解約しました。')
    return redirect('subsc_register')


# ==========================================
# 3. IC関連情報登録 (IC Register)
# ==========================================
def ic_register(request):
    link_id = request.session.get('link_id', 'dummy-link-uuid')

    if request.method == 'POST':
        ic_type = request.POST.get('ic_type')
        ic_idm = request.POST.get('ic_idm')
        card_alias = request.POST.get('card_alias')

        messages.success(request, f'ICカード情報（{card_alias}）を登録しました。')
        return redirect('ic_register')

    return render(request, 'ic_register.html')


# ==========================================
# 4. 利用者一覧 (User List - 管理者用)
# ==========================================
def user_list(request):
    keyword = request.GET.get('keyword', '')
    status_filter = request.GET.get('status', '')

    queryset = Subsc.objects.select_related('plan').all().order_by('-created_at')

    if keyword:
        queryset = queryset.filter(link_id__icontains=keyword)
    if status_filter:
        queryset = queryset.filter(subsc_status=status_filter)

    paginator = Paginator(queryset, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'user_list.html', {
        'page_obj': page_obj,
        'keyword': keyword,
        'status_filter': status_filter,
    })


def user_detail(request, link_id):
    subsc = get_object_or_404(Subsc, link_id=link_id)
    return render(request, 'user_detail.html', {'subsc': subsc})


# ==========================================
# 5. 移動情報一覧 (Movement List - 管理者用)
# ==========================================
def movement_list(request):
    link_id = request.GET.get('link_id', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    transport_type = request.GET.get('transport_type', '')

    movements = [
        {
            'id': 1001,
            'link_id': '550e8400-e29b-41d4-a716-446655440000',
            'user_name': '山田 太郎',
            'ride_datetime': '2026-11-26 08:15:00',
            'getoff_datetime': '2026-11-26 08:45:00',
            'departure': '大分駅',
            'arrival': '別府駅',
            'transport': '鉄道',
            'fare': 280,
            'ic_idm': '0101011234567890'
        },
    ]

    return render(request, 'movement_list.html', {
        'movements': movements,
        'link_id': link_id,
        'date_from': date_from,
        'date_to': date_to,
        'transport_type': transport_type,
    })