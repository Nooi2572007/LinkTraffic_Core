from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


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
        validators=[MinValueValidator(1), MaxValueValidator(999999)]
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