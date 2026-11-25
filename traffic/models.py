from django.db import models


# Create your models here.
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Prefecture(models.Model):
    """都道府県テーブル"""

    # 都道府県コード：INTEGER / 桁数2 / PK / NN
    prefecture_code = models.IntegerField(
        verbose_name="都道府県コード",
        primary_key=True,
        validators=[MinValueValidator(1), MaxValueValidator(99)],  # 2桁
    )
    # 都道府県名：VARCHAR / 桁数5 / NN（例：神奈川県、和歌山県、鹿児島県）
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
    """エリア情報テーブル"""

    # エリアコード：INTEGER / 桁数6 / PK / NN
    # 備考：「都道府県コード(2桁) + 0 + 連番(3桁)」 例）13 + 0 + 001 → 130001 ※2桁+0+3桁で6桁
    area_code = models.IntegerField(
        verbose_name="エリアコード",
        primary_key=True,
        validators=[MinValueValidator(1), MaxValueValidator(999999)],  # 6桁
    )
    # エリア名：VARCHAR / 桁数255 / NN
    area_name = models.CharField(
        verbose_name="エリア名",
        max_length=255,
    )
    # 都道府県コード：INTEGER / 桁数2 / FK / NN（カラム名は prefecture_code）
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