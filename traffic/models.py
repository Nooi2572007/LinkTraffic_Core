from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


# ==========================================
# 都道府県・エリア（既存）
# ==========================================
class Prefecture(models.Model):
    prefecture_code = models.IntegerField(
        verbose_name="都道府県コード",
        primary_key=True,
        validators=[MinValueValidator(1), MaxValueValidator(99)],  # 2桁
    )
    prefecture_name = models.CharField(
        verbose_name="都道府県名",
        max_length=5,
    )

    class Meta:
        db_table = "prefecture"
        verbose_name = "都道府県"
        verbose_name_plural = "都道府県"
        ordering = ["prefecture_code"]

    def __str__(self):
        return self.prefecture_name


class Area(models.Model):
    area_code = models.IntegerField(
        verbose_name="エリアコード",
        primary_key=True,
        validators=[MinValueValidator(1), MaxValueValidator(999999)],
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

    def __str__(self):
        return self.area_name


# ==========================================
# 駅・路線・駅路線接続（新規追加）
# ==========================================
class Station(models.Model):
    station_code = models.IntegerField(
        verbose_name="駅コード",
        primary_key=True,
        validators=[MinValueValidator(1), MaxValueValidator(9999999)],  # 7桁
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

    def __str__(self):
        return self.station_name


class Line(models.Model):
    line_code = models.IntegerField(
        verbose_name="路線コード",
        primary_key=True,
        validators=[MinValueValidator(1), MaxValueValidator(9999)],  # 4桁
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

    def __str__(self):
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

    def __str__(self):
        return f"{self.station} - {self.line}"


# ==========================================
# ICカード利用者・移動情報（新規追加）
# ==========================================
class IcUser(models.Model):
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
        validators=[MinValueValidator(0), MaxValueValidator(99)],  # 2桁
    )
    sex = models.IntegerField(
        verbose_name="性別",
        validators=[MinValueValidator(0), MaxValueValidator(9)],  # 1桁
    )
    age = models.IntegerField(
        verbose_name="年齢",
        validators=[MinValueValidator(0), MaxValueValidator(999)],  # 3桁
    )
    commuter_pass = models.BooleanField(
        verbose_name="定期情報",
    )
    inserted_by = models.CharField(
        verbose_name="登録者ID",
        max_length=9,
    )
    inserted_at = models.DateTimeField(
        verbose_name="登録日",
        auto_now_add=True,
    )

    class Meta:
        db_table = "ic_users"
        verbose_name = "ICカード利用者情報管理"
        verbose_name_plural = "ICカード利用者情報管理"
        ordering = ["ic_user_id"]

    def __str__(self):
        return self.card_id


class IcMovement(models.Model):
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
        validators=[MinValueValidator(0), MaxValueValidator(99)],  # 2桁
    )
    inserted_by = models.CharField(
        verbose_name="登録者ID",
        max_length=9,
    )
    inserted_at = models.DateTimeField(
        verbose_name="登録日",
        auto_now_add=True,
    )

    class Meta:
        db_table = "ic_movement"
        verbose_name = "ICカード移動情報管理"
        verbose_name_plural = "ICカード移動情報管理"
        ordering = ["ic_movement_id"]

    def __str__(self):
        return f"{self.card_id}: {self.departure_station} -> {self.arrival_station}"


# ==========================================
# システム管理（必要なければ削除可）
# ==========================================
class System(models.Model):
    class MaintenanceStatus(models.TextChoices):
        ACTIVE = "active", "稼働中"
        MAINTENANCE = "maintenance", "通常メンテ"
        EMERGENCY = "emergency", "緊急メンテ"

    system_event_id = models.BigAutoField(
        verbose_name="ユニークID",
        primary_key=True,
    )
    admin_id = models.CharField(
        verbose_name="管理者ID",
        max_length=9,
        null=True,
        blank=True,
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

    def __str__(self):
        return f"{self.get_maintenance_display()} ({self.system_event_id})"