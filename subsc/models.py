import uuid, hashlib, secrets
from django.db import models


class TimeStampModel(models.Model):
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='作成日時',
    )
    updated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='更新日時',
    )

    class Meta:
        abstract = True


class LinkIdMixin(models.Model):
    link_id = models.UUIDField(
        db_index=True,
        verbose_name='接続ID',
    )

    class Meta:
        abstract = True


def hash_with_salt(raw_value: str, salt: str | None = None) -> str:
    if raw_value is None or str(raw_value) == '':
        raise ValueError('ハッシュ化対象の値が空です。')
    if salt is None:
        salt = secrets.token_hex(16)
    digest = hashlib.sha256(f'{salt}:{raw_value}'.encode('utf-8')).hexdigest()
    return f'{salt}${digest}'

def verify_salted_hash(raw_value: str, stored_value: str) -> bool:
    if not stored_value or '$' not in stored_value:
        return False
    salt, expected_digest = stored_value.split('$', 1)
    actual_digest = hashlib.sha256(f'{salt}:{raw_value}'.encode('utf-8')).hexdigest()
    return secrets.compare_digest(actual_digest, expected_digest)


class SubscPlan(TimeStampModel):
    plan_id = models.BigAutoField(
        primary_key=True,
        verbose_name='プランID',
    )
    plan_name = models.CharField(
        max_length=255,
        verbose_name='プラン名',
    )
    plan_price = models.IntegerField(
        default=0,
        verbose_name='金額',
    )
    plan_interval = models.IntegerField(
        default=0,
        verbose_name='更新間隔',
    )
    plan_explanation = models.CharField(
        max_length=255,
        verbose_name='プラン説明',
    )
    status = models.BooleanField(
        default=True,
        verbose_name='プランステータス',
    )
    created_by = models.ForeignKey(
        'account.Admin',
        to_field='admin_id',
        db_column='created_by',
        on_delete=models.PROTECT,
        related_name='created_subsc_plans',
        verbose_name='作成者ID',
    )
    updated_by = models.ForeignKey(
        'account.Admin',
        to_field='admin_id',
        db_column='updated_by',
        on_delete=models.PROTECT,
        related_name='updated_subsc_plans',
        null=True,
        blank=True,
        verbose_name='更新者ID',
    )
    
    class Meta(TimeStampModel.Meta):
        db_table = 'subsc_plan'
        verbose_name = 'サブスクプラン'
        verbose_name_plural = 'サブスクプラン'

    def __str__(self):
        return self.plan_name


class Subsc(TimeStampModel, LinkIdMixin):
    class SubscStatus(models.TextChoices):
        ACTIVE = 'active', '有効'
        UNSUBSCRIBE = 'unsubscribe', '解約済み'
        ERROR = 'error', 'エラー'

    subsc_id = models.BigAutoField(
        primary_key=True,
        verbose_name='サブスクID',
    )
    plan = models.ForeignKey(
        SubscPlan,
        on_delete=models.PROTECT,
        db_column='plan_id',
        verbose_name='プランID',
    )
    subsc_status = models.CharField(
        max_length=20,
        choices=SubscStatus.choices,
        default=SubscStatus.ERROR,
        db_index=True,
        verbose_name='サブスクステータス',
    )
    next_subsc_date = models.DateField(
        verbose_name='次回更新日',
    )
    unsubscribed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='解約日時',
    )

    class Meta(TimeStampModel.Meta):
        db_table = 'subsc'
        verbose_name = 'サブスク管理'
        verbose_name_plural = 'サブスク管理'

    def __str__(self):
        return f'{self.subsc_id} ({self.subsc_status})'


class Credit(TimeStampModel, LinkIdMixin):
    class CardBrand(models.TextChoices):
        VISA = 'visa', 'VISA'
        MASTERCARD = 'mastercard', 'Mastercard'
        JCB = 'jcb', 'JCB'
        AMEX = 'amex', 'American Express'
        NONE = 'none', 'NONE'
    
    credit_pay_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='クレジットID',
    )
    card_holder_name = models.CharField(
        max_length=100,
        verbose_name="カード名義人"
    )
    card_brand = models.CharField(
        max_length=20,
        choices=CardBrand.choices,
        default=CardBrand.NONE,
        verbose_name='カードブランド',
    )
    last_card_number = models.CharField(
        max_length=4,
        verbose_name='カード下4桁',
    )
    exp_month = models.IntegerField(
        verbose_name='有効期限（月）',
    )
    exp_year = models.IntegerField(
        verbose_name='有効期限（年）',
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='削除日時',
    )

    class Meta(TimeStampModel.Meta):
        db_table = 'credit'
        verbose_name = 'クレジットカード管理'
        verbose_name_plural = 'クレジットカード管理'

    def __str__(self):
        return f'{self.get_card_brand_display()} (下4桁{self.last_card_number})'


class Bank(TimeStampModel, LinkIdMixin):
    class AccountType(models.IntegerChoices):
        ORDINARY = 1, '普通'
        CHECKING = 2, '当座'

    class AccountNameType(models.IntegerChoices):
        INDIVIDUAL = 1, '個人'
        CORPORATE = 2, '法人'

    bankpay_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='銀行振替ID',
    )
    bank_code = models.CharField(
        max_length=128,
        verbose_name='金融機関コード',
    )
    bank_name = models.CharField(
        max_length=128,
        verbose_name='金融機関名',
    )
    bank_branch_code = models.CharField(
        max_length=128,
        verbose_name='支店コード',
    )
    bank_branch_name = models.CharField(
        max_length=128,
        verbose_name='支店名',
    )
    bank_account_type = models.SmallIntegerField(
        choices=AccountType.choices,
        default=AccountType.ORDINARY,
        verbose_name='口座種別',
    )
    bank_account_name_type = models.SmallIntegerField(
        choices=AccountNameType.choices,
        default=AccountNameType.INDIVIDUAL,
        verbose_name='口座名義の区分',
    )
    bank_account_number = models.CharField(
        max_length=128,
        verbose_name='口座番号',
    )
    bank_account_holder_name = models.CharField(
        max_length=100,
        verbose_name='口座名義人（カナ）',
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='削除日時',
    )

    class Meta(TimeStampModel.Meta):
        db_table = 'bank'
        verbose_name = '銀行振替管理'
        verbose_name_plural = '銀行振替管理'
    
    def set_bank_info(
        self,
        *,
        bank_code: str,
        bank_name: str,
        bank_branch_code: str,
        bank_branch_name: str,
        bank_account_number: str,
        ) -> None:
        self.bank_code = hash_with_salt(bank_code)
        self.bank_name = hash_with_salt(bank_name)
        self.bank_branch_code = hash_with_salt(bank_branch_code)
        self.bank_branch_name = hash_with_salt(bank_branch_name)
        self.bank_account_number = hash_with_salt(bank_account_number)

    def __str__(self):
        return str(self.bankpay_id)

class Payment(TimeStampModel):
    class PaymentMethod(models.TextChoices):
        CREDIT = "credit", "クレジットカード"
        BANK = "bank", "銀行振込"
        ERROR = "error", "エラー"

    class PaymentStatus(models.TextChoices):
        PAID = "paid", "支払い済み"
        UNPAID = "unpaid", "未払い"
        REFUNDED = "refunded", "返金済み"
        ERROR = "error", "エラー"

    payment_id = models.BigAutoField(
        primary_key=True,
        verbose_name="決済ID",
    )
    subsc = models.ForeignKey(
        Subsc,
        on_delete=models.PROTECT,
        db_column="subsc_id",
        related_name="payments",
        verbose_name="サブスクID",
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        verbose_name="決済手段",
    )
    credit_pay = models.ForeignKey(
        Credit,
        to_field="credit_pay_id",
        on_delete=models.PROTECT,
        db_column="credit_pay_id",
        related_name="payments",
        null=True,
        blank=True,
        verbose_name="クレジットID",
    )
    bankpay = models.ForeignKey(
        Bank,
        to_field="bankpay_id",
        on_delete=models.PROTECT,
        db_column="bankpay_id",
        related_name="payments",
        null=True,
        blank=True,
        verbose_name="銀行振替ID",
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.ERROR,
        db_index=True,
        verbose_name="決済ステータス",
    )
    amount = models.IntegerField(
        verbose_name="金額",
    )
    gateway_payment_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="外部決済トランザクションID",
    )
    error_message = models.TextField(
        null=True,
        blank=True,
        verbose_name="外部決済リターンメッセージ",
    )
    paid_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="決済完了日時",
    )

    class Meta(TimeStampModel.Meta):
        db_table = "payment"
        verbose_name = "決済管理"
        verbose_name_plural = "決済管理"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.payment_id} ({self.get_payment_status_display()})"