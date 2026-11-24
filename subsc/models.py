import uuid
from django.db import models


class SubscPlan(models.Model):
    """サブスクプラン"""
    plan_id = models.BigAutoField(primary_key=True, verbose_name='プランID')
    plan_name = models.CharField(max_length=255, verbose_name='プラン名')
    plan_price = models.IntegerField(default=0, verbose_name='金額')
    plan_interval = models.IntegerField(default=0, verbose_name='更新間隔', help_text='単位は「月」')
    plan_explanation = models.CharField(max_length=255, verbose_name='プラン説明')
    status = models.BooleanField(default=True, verbose_name='プランステータス', help_text='プランが現在有効かどうか')
    created_by = models.BigIntegerField(verbose_name='作成者ID', help_text='管理者ID')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_by = models.CharField(max_length=9, null=True, blank=True, verbose_name='更新者ID', help_text='管理者ID')
    updated_at = models.DateTimeField(null=True, blank=True, verbose_name='変更日時', help_text='無効にした時に記載する')

    class Meta:
        db_table = 'subsc_plan'
        verbose_name = 'サブスクプラン'
        verbose_name_plural = 'サブスクプラン'

    def __str__(self):
        return self.plan_name


class Subsc(models.Model):
    """サブスク管理"""
    class SubscStatus(models.TextChoices):
        ACTIVE = 'active', '有効'
        UNSUBSCRIBE = 'unsubscribe', '解約済み'
        ERROR = 'error', 'エラー'

    subsc_id = models.BigAutoField(primary_key=True, verbose_name='サブスクID')
    link_id = models.CharField(max_length=36, verbose_name='接続ID', help_text='UUID')
    plan = models.ForeignKey(
        SubscPlan,
        on_delete=models.PROTECT,
        db_column='plan_id',
        verbose_name='プランID'
    )
    subsc_status = models.CharField(
        max_length=20,
        choices=SubscStatus.choices,
        default=SubscStatus.ERROR,
        verbose_name='サブスクステータス'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='登録日時')
    next_subsc_date = models.DateField(verbose_name='次回更新日', help_text='登録時に計算して登録')
    updated_at = models.DateTimeField(null=True, blank=True, verbose_name='更新日時')
    unsubscribed_at = models.DateTimeField(null=True, blank=True, verbose_name='解約日時')

    class Meta:
        db_table = 'subsc'
        verbose_name = 'サブスク管理'
        verbose_name_plural = 'サブスク管理'

    def __str__(self):
        return f"{self.subsc_id} ({self.subsc_status})"


class Credit(models.Model):
    """クレジットカード管理"""
    credit_pay_id = models.CharField(
        max_length=36,
        primary_key=True,
        default=uuid.uuid4,
        verbose_name='クレジットID',
        help_text='UUID'
    )
    link_id = models.CharField(max_length=36, verbose_name='接続ID', help_text='UUID')
    card_holder_name = models.CharField(max_length=100, null=True, blank=True, verbose_name='カード名義人')
    last_card_number = models.CharField(max_length=4, verbose_name='カード下4桁')
    exp_month = models.IntegerField(verbose_name='有効期限（月）')
    exp_year = models.IntegerField(verbose_name='有効期限（年）')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(null=True, blank=True, verbose_name='更新日時')
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name='削除日時')

    class Meta:
        db_table = 'credit'
        verbose_name = 'クレジットカード管理'
        verbose_name_plural = 'クレジットカード管理'

    def __str__(self):
        return f"****-****-****-{self.last_card_number}"


class Bank(models.Model):
    """銀行振替管理"""
    class AccountType(models.IntegerChoices):
        ORDINARY = 1, '普通'
        CHECKING = 2, '当座'

    class AccountNameType(models.IntegerChoices):
        INDIVIDUAL = 1, '個人'
        CORPORATE = 2, '法人'

    bankpay_id = models.CharField(
        max_length=36,
        primary_key=True,
        default=uuid.uuid4,
        verbose_name='銀行振替ID',
        help_text='UUID'
    )
    link_id = models.CharField(max_length=36, verbose_name='接続ID', help_text='UUID')
    bank_code = models.CharField(max_length=4, verbose_name='金融機関コード', help_text='ハッシュ化')
    bank_name = models.CharField(max_length=50, verbose_name='金融機関名', help_text='ハッシュ化')
    bank_branch_code = models.CharField(max_length=3, verbose_name='支店コード', help_text='ハッシュ化')
    bank_branch_name = models.CharField(max_length=50, verbose_name='支店名', help_text='ハッシュ化')
    bank_account_type = models.SmallIntegerField(
        choices=AccountType.choices,
        default=AccountType.ORDINARY,
        verbose_name='口座種別'
    )
    bank_account_name_type = models.SmallIntegerField(
        choices=AccountNameType.choices,
        default=AccountNameType.INDIVIDUAL,
        verbose_name='口座名義の区分'
    )
    bank_account_number = models.CharField(max_length=20, verbose_name='口座番号', help_text='ハッシュ化')
    bank_account_holder_name = models.CharField(max_length=100, verbose_name='口座名義人（カナ）')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(null=True, blank=True, verbose_name='更新日時')
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name='削除日時')

    class Meta:
        db_table = 'bank'
        verbose_name = '銀行振替管理'
        verbose_name_plural = '銀行振替管理'

    def __str__(self):
        return self.bankpay_id


class Payment(models.Model):
    """決済管理"""
    class PaymentMethod(models.TextChoices):
        CREDIT = 'credit', 'クレジットカード'
        BANK = 'bank', '銀行振替'
        ERROR = 'error', 'エラー'

    class PaymentStatus(models.TextChoices):
        PAID = 'paid', '支払い済み'
        UNPAID = 'unpaid', '未払い'
        REFUNDED = 'refunded', '返金済み'
        ERROR = 'error', 'エラー'

    payment_id = models.BigAutoField(primary_key=True, verbose_name='決済ID')
    subsc = models.ForeignKey(
        Subsc,
        on_delete=models.PROTECT,
        db_column='subsc_id',
        verbose_name='サブスクID'
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        verbose_name='決済手段'
    )
    credit_pay = models.ForeignKey(
        Credit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='credit_pay_id',
        verbose_name='クレジットID'
    )
    bankpay = models.ForeignKey(
        Bank,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='bankpay_id',
        verbose_name='銀行振替ID'
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.ERROR,
        verbose_name='決済ステータス'
    )
    amount = models.IntegerField(verbose_name='金額')
    gateway_payment_id = models.CharField(max_length=100, verbose_name='外部決済トランザクションID')
    error_message = models.TextField(null=True, blank=True, verbose_name='外部決済リターンメッセージ')
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name='決済完了日時')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(null=True, blank=True, verbose_name='更新日時')

    class Meta:
        db_table = 'payment'
        verbose_name = '決済管理'
        verbose_name_plural = '決済管理'

    def __str__(self):
        return f"{self.payment_id} - {self.payment_status}"