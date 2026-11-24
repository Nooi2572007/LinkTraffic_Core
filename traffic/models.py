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