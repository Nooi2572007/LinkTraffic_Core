from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

def digits_validator(digits: int, min_value: int = 0) -> list:
    """指定桁数（正の整数）の範囲バリデータを返す。"""
    max_value = (10**digits) - 1
    return [MinValueValidator(min_value), MaxValueValidator(max_value)]


class Prefecture(models.Model):
    prefecture_code = models.IntegerField(
        verbose_name="都道府県コード",
        primary_key=True,
        validators=digits_validator(2, min_value=1),
    )
    prefecture_name = models.CharField(
        verbose_name="都道府県名",
        max_length=5,
    )

    class Meta:
        db_table = "prefectures"
        verbose_name = "都道府県"
        verbose_name_plural = "都道府県"
        ordering = ["prefecture_code"]

    def __str__(self) -> str:
        return self.prefecture_name


class Area(models.Model):
    area_code = models.IntegerField(
        verbose_name="エリアコード",
        primary_key=True,
        validators=digits_validator(6, min_value=1),
    )
    area_name = models.CharField(
        verbose_name="エリア名",
        max_length=255,
    )
    prefecture = models.ForeignKey(
        Prefecture,
        verbose_name="都道府県コード",
        db_column="prefecture_code",
        on_delete=models.PROTECT,
        related_name="areas",
    )

    class Meta:
        db_table = "areas"
        verbose_name = "エリア情報"
        verbose_name_plural = "エリア情報"
        ordering = ["area_code"]

    def __str__(self) -> str:
        return self.area_name


class Station(models.Model):
    station_code = models.IntegerField(
        verbose_name="駅コード",
        primary_key=True,
        validators=digits_validator(7, min_value=1),
    )
    station_name = models.CharField(
        verbose_name="駅名",
        max_length=255,
    )
    area = models.ForeignKey(
        Area,
        verbose_name="エリアコード",
        db_column="area_code",
        on_delete=models.PROTECT,
        related_name="stations",
    )

    class Meta:
        db_table = "stations"
        verbose_name = "駅管理"
        verbose_name_plural = "駅管理"
        ordering = ["station_code"]

    def __str__(self) -> str:
        return self.station_name


class Line(models.Model):
    line_code = models.IntegerField(
        verbose_name="路線コード",
        primary_key=True,
        validators=digits_validator(4, min_value=1),
    )
    line_name = models.CharField(
        verbose_name="路線名",
        max_length=255,
    )

    class Meta:
        db_table = "lines"
        verbose_name = "路線管理"
        verbose_name_plural = "路線管理"
        ordering = ["line_code"]

    def __str__(self) -> str:
        return self.line_name


class StationLine(models.Model):
    station = models.ForeignKey(
        Station,
        verbose_name="駅コード",
        db_column="station_code",
        on_delete=models.PROTECT,
        related_name="station_lines",
    )
    line = models.ForeignKey(
        Line,
        verbose_name="路線コード",
        db_column="line_code",
        on_delete=models.PROTECT,
        related_name="station_lines",
    )

    class Meta:
        db_table = "station_lines"
        verbose_name = "駅路線接続管理"
        verbose_name_plural = "駅路線接続管理"
        constraints = [
            models.UniqueConstraint(
                fields=["station", "line"],
                name="unique_station_line",
            )
        ]

    def __str__(self) -> str:
        return f"{self.station} - {self.line}"


class InsertedAtMixin(models.Model):
    inserted_at = models.DateTimeField(
        verbose_name="登録日",
        auto_now_add=True,
    )

    class Meta:
        abstract = True


class AdminInsertedMixin(InsertedAtMixin):
    inserted_by = models.ForeignKey(
        "account.Admin",
        to_field="admin_id",
        db_column="inserted_by",
        verbose_name="登録者ID",
        on_delete=models.PROTECT,
        related_name="%(class)s_inserted",
    )

    class Meta:
        abstract = True


class IcUser(AdminInsertedMixin):
    class SexCode(models.IntegerChoices):
        MALE = 1, "男"
        FEMALE = 2, "女"
        OTHER = 3, "その他"

    class CardTypeCode(models.IntegerChoices):
        ADULT = 1, "大人"
        CHILD = 2, "小人"
        THE_DISABLED = 3, "障がい者"

    ic_user_id = models.BigIntegerField(
        verbose_name="ユニークID",
        unique=True,
    )
    card_id = models.CharField(
        verbose_name="カード番号",
        max_length=17,
        primary_key=True,
    )
    card_type = models.IntegerField(
        verbose_name="カード種別",
        choices=CardTypeCode.choices,
        validators=digits_validator(2, min_value=1),
    )
    sex = models.IntegerField(
        verbose_name="性別",
        choices=SexCode.choices,
        validators=digits_validator(1, min_value=1),
    )
    age = models.IntegerField(
        verbose_name="年齢",
        validators=digits_validator(3),
    )
    commuter_pass = models.BooleanField(
        verbose_name="定期情報",
        default=False
    )
    class Meta:
        db_table = "ic_users"
        verbose_name = "ICカード利用者情報管理"
        verbose_name_plural = "ICカード利用者情報管理"
        ordering = ["ic_user_id"]

    def __str__(self) -> str:
        return self.card_id


class IcMovement(AdminInsertedMixin):
    class UseTypeCode(models.IntegerChoices):
        SF = 1, "SF"
        COMMUTER = 2, "定期"

    ic_movement_id = models.BigAutoField(
        verbose_name="ユニークID",
        primary_key=True,
    )
    card = models.ForeignKey(
        IcUser,
        verbose_name="カード番号",
        db_column="card_id",
        on_delete=models.PROTECT,
        related_name="movements",
    )
    departure_station = models.ForeignKey(
        Station,
        verbose_name="乗車駅",
        db_column="departure_station",
        on_delete=models.PROTECT,
        related_name="departure_movements",
    )
    departure_date = models.DateTimeField(
        verbose_name="入場日時",
    )
    arrival_station = models.ForeignKey(
        Station,
        verbose_name="降車駅",
        db_column="arrival_station",
        on_delete=models.PROTECT,
        related_name="arrival_movements",
    )
    arrival_date = models.DateTimeField(
        verbose_name="出場日時",
    )
    use_type = models.IntegerField(
        verbose_name="利用種別",
        choices=UseTypeCode.choices,
        validators=digits_validator(2, min_value=1),
    )

    class Meta:
        db_table = "ic_movement"
        verbose_name = "ICカード移動情報管理"
        verbose_name_plural = "ICカード移動情報管理"
        ordering = ["ic_movement_id"]
        indexes = [
            models.Index(fields=["departure_date"], name="idx_ic_move_dep_date"),
            models.Index(fields=["arrival_date"], name="idx_ic_move_arr_date"),
        ]

    def __str__(self) -> str:
        return f"{self.card_id}: {self.departure_station_id} -> {self.arrival_station_id}"


class System(models.Model):
    class MaintenanceStatus(models.TextChoices):
        ACTIVE = "active", "稼働中"
        MAINTENANCE = "maintenance", "通常メンテナンス"
        EMERGENCY = "emergency", "緊急メンテナンス"

    system_event_id = models.BigAutoField(
        verbose_name="ユニークID",
        primary_key=True,
    )
    admin_id = models.ForeignKey(
        "account.Admin",
        to_field="admin_id",
        verbose_name="管理者ID",
        db_column="admin_id",
        on_delete=models.PROTECT,
    )
    maintenance = models.CharField(
        verbose_name="メンテナンス",
        max_length=255,
        choices=MaintenanceStatus.choices,
        default=MaintenanceStatus.ACTIVE,
    )
    maintenance_content = models.TextField(
        verbose_name="メンテナンス内容",
        null=True,
        blank=True,
    )
    maintenance_end_time = models.DateTimeField(
        verbose_name="終了予定日時",
        null=True,
        blank=True,
    )
    updated_at = models.DateTimeField(
        verbose_name="最終更新日時",
        auto_now=True,
    )

    class Meta:
        db_table = "system"
        verbose_name = "システム"
        verbose_name_plural = "システム"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["maintenance", "updated_at"], name="idx_sys_maint_updated"),
        ]

    def __str__(self) -> str:
        return f"{self.get_maintenance_display()} ({self.system_event_id})"