from django.db import models

# Create your models here.
import uuid
from django.db import models


class User(models.Model):
    class UserStatus(models.TextChoices):
        ACTIVE = 'active', '有効'
        LOOK = 'look', 'ロック'  # ※定義書表記通り（lockの誤記の場合は修正してください）
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
    link_id = models.CharField(
        max_length=36,
        default=lambda: str(uuid.uuid4()),
        editable=False,
        verbose_name='接続ID',
    )
    company_name = models.CharField(
        max_length=255,
        verbose_name='会社名',
    )
    email = models.EmailField(
        max_length=255,
        verbose_name='メールアドレス',
    )
    password = models.CharField(
        max_length=255,
        verbose_name='パスワード',
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
        null=True,
        blank=True,
        verbose_name='郵便番号',
    )
    address = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name='住所',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='登録日時',
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
        db_table = 'users'
        verbose_name = '利用者'
        verbose_name_plural = '利用者'

    def __str__(self):
        return f'{self.company_name} ({self.email})'
from django.db import models


class Admin(models.Model):
    admin_id = models.BigAutoField(
        primary_key=True,
        verbose_name='管理者ID',
    )
    name = models.CharField(
        max_length=255,
        verbose_name='氏名',
    )
    email = models.EmailField(
        max_length=255,
        verbose_name='メールアドレス',
    )
    password = models.CharField(
        max_length=255,
        verbose_name='パスワード',
    )
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
        db_table = 'admins'
        verbose_name = '管理者'
        verbose_name_plural = '管理者'

    def __str__(self):
        return f'{self.name} ({self.email})'