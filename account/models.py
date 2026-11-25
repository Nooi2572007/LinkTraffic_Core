from django.db import models
from django.contrib.auth.hashers import check_password, make_password
from django.core.validators import RegexValidator
import uuid

admin_id_validator = RegexValidator(
    regex=r'^@LTA[0-9]{5}$',
    message='管理者IDは「@LTA」+半角数字5桁で入力してください（全角数字は不可）',
)


class TimeSoftDeleteModel(models.Model):
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='作成日時',
    )
    updated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='更新日時',
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='削除日時',
    )

    class Meta:
        abstract = True


class PasswordMixin(models.Model):
    password = models.CharField(
        max_length=255,
        verbose_name='パスワード',
    )

    class Meta:
        abstract = True

    def set_password(self, raw_password):
        if not raw_password:
            raise ValueError('パスワードは空にできません。')
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)


class User(TimeSoftDeleteModel, PasswordMixin):
    class UserStatus(models.TextChoices):
        ACTIVE = 'active', '有効'
        LOCK = 'lock', 'ロック'
        NONE = 'none', 'なし'

    class Industry(models.IntegerChoices):
        IT_TELECOM = 1, 'IT・通信・インターネット'
        TRANSPORT_LOGISTICS = 2, '運輸・物流・交通'
        MANUFACTURING = 3, '製造業・メーカー'
        TRADING_RETAIL = 4, '商社・卸売・小売'
        REAL_ESTATE_CONSTRUCTION = 5, '不動産・建設'
        HOSPITALITY_FOOD_TOURISM = 6, '宿泊・飲食・観光'
        FINANCE_INSURANCE = 7, '金融・保険'
        MEDICAL_WELFARE = 8, '医療・福祉'
        EDUCATION_LEARNING = 9, '教育・学習支援'
        GOVERNMENT_MUNICIPALITY = 10, '官公庁・自治体'
        PROFESSIONAL_ADVERTISING = 11, '専門サービス・広告'
        OTHER = 12, 'その他'

    user_id = models.BigAutoField(
        primary_key=True,
        verbose_name='利用者ID',
    )
    link_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        verbose_name='接続ID',
    )
    company_name = models.CharField(
        max_length=255,
        verbose_name='会社名',
    )
    email = models.EmailField(
        max_length=255,
        unique=True,
        verbose_name='メールアドレス',
    )
    phone_number = models.CharField(
        max_length=20,
        verbose_name='電話番号',
    )
    user_status = models.CharField(
        max_length=20,
        choices=UserStatus.choices,
        default=UserStatus.ACTIVE,
        verbose_name='アカウントステータス',
    )
    industry = models.PositiveSmallIntegerField(
        choices=Industry.choices,
        verbose_name='業種',
    )
    post_code = models.IntegerField(
        verbose_name='郵便番号',
    )
    address = models.CharField(
        max_length=255,
        verbose_name='住所',
    )

    class Meta(TimeSoftDeleteModel.Meta):
        db_table = 'users'
        verbose_name = '利用者'
        verbose_name_plural = '利用者'

    def __str__(self):
        return f'{self.company_name} ({self.email})'


class Admin(TimeSoftDeleteModel, PasswordMixin):
    admin_id = models.CharField(
        max_length=9,
        primary_key=True,
        validators=[admin_id_validator],
        verbose_name='管理者ID',
    )
    name = models.CharField(
        max_length=255,
        verbose_name='氏名',
    )

    class Meta(TimeSoftDeleteModel.Meta):
        db_table = 'admins'
        verbose_name = '管理者'
        verbose_name_plural = '管理者'

    def __str__(self):
        return f'{self.name} ({self.admin_id})'