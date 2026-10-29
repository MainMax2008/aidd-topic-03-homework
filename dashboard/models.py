from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

# Начальный баланс виртуального портфеля
INITIAL_BALANCE = Decimal("100000.00")


class Share(models.Model):
    """Акция"""

    figi = models.CharField(max_length=255, unique=True)
    isin = models.CharField(max_length=255)
    name = models.CharField(max_length=255, verbose_name="Наименование компании")
    ticker = models.CharField(max_length=10, unique=True, verbose_name="Тикер")
    currency = models.CharField(max_length=20, verbose_name="Валюта")
    uid = models.CharField(max_length=255, unique=True)
    last_price = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        blank=True,
        null=True,
        verbose_name="Текущая цена",
    )
    is_trend_high = models.BooleanField(
        blank=True, null=True, verbose_name="Растет цена"
    )
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        verbose_name = "Акция"
        verbose_name_plural = "Акции"

    def __str__(self):
        return f"{self.name} ({self.ticker})"


class Portfolio(models.Model):
    """Виртуальный инвестиционный портфель"""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="portfolio",
        verbose_name="Пользователь",
    )
    balance = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=INITIAL_BALANCE,
        verbose_name="Баланс",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Портфель"
        verbose_name_plural = "Портфели"

    def __str__(self):
        return f"Портфель пользователя {self.user}"

    @property
    def total_positions_value(self):
        """Общая стоимость открытых позиций по текущим ценам"""
        return sum(
            (position.current_value for position in self.positions.all()),
            Decimal("0.00"),
        )

    @property
    def total_value(self):
        """Общая стоимость портфеля (баланс + позиции)"""
        return self.balance + self.total_positions_value


class PortfolioPosition(models.Model):
    """Открытая позиция по акции в портфеле"""

    portfolio = models.ForeignKey(
        Portfolio,
        on_delete=models.CASCADE,
        related_name="positions",
        verbose_name="Портфель",
    )
    share = models.ForeignKey(
        Share,
        on_delete=models.CASCADE,
        related_name="positions",
        verbose_name="Акция",
    )
    quantity = models.PositiveIntegerField(verbose_name="Количество")
    average_price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        verbose_name="Средняя цена",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Позиция"
        verbose_name_plural = "Позиции"
        constraints = [
            models.UniqueConstraint(
                fields=["portfolio", "share"],
                name="unique_portfolio_share_position",
            )
        ]

    def __str__(self):
        return f"{self.share.ticker} x{self.quantity} в портфеле {self.portfolio_id}"

    @property
    def current_price(self):
        """Текущая цена акции (0, если цена неизвестна)"""
        return self.share.last_price or Decimal("0")

    @property
    def current_value(self):
        """Текущая стоимость позиции"""
        return (Decimal(self.quantity) * self.current_price).quantize(Decimal("0.01"))

    @property
    def pnl(self):
        """Прибыль/убыток позиции относительно средней цены покупки"""
        return (
            (self.current_price - self.average_price) * Decimal(self.quantity)
        ).quantize(Decimal("0.01"))


class Transaction(models.Model):
    """Сделка покупки/продажи акций в портфеле"""

    class TransactionType(models.TextChoices):
        BUY = "BUY", "Покупка"
        SELL = "SELL", "Продажа"

    portfolio = models.ForeignKey(
        Portfolio,
        on_delete=models.CASCADE,
        related_name="transactions",
        verbose_name="Портфель",
    )
    share = models.ForeignKey(
        Share,
        on_delete=models.CASCADE,
        related_name="transactions",
        verbose_name="Акция",
    )
    transaction_type = models.CharField(
        max_length=4,
        choices=TransactionType.choices,
        verbose_name="Тип сделки",
    )
    quantity = models.PositiveIntegerField(verbose_name="Количество")
    price = models.DecimalField(max_digits=12, decimal_places=4, verbose_name="Цена")
    total_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        verbose_name="Сумма сделки",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name="Дата сделки",
    )

    class Meta:
        verbose_name = "Сделка"
        verbose_name_plural = "Сделки"
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.get_transaction_type_display()}: "
            f"{self.quantity} {self.share.ticker} по {self.price}"
        )


@receiver(post_save, sender=get_user_model())
def create_user_portfolio(sender, instance, created, **kwargs):
    """Автоматическое создание портфеля при создании пользователя"""
    if created:
        Portfolio.objects.get_or_create(user=instance)
