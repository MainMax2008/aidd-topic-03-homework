from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction

from dashboard.models import INITIAL_BALANCE, Portfolio, PortfolioPosition, Share, Transaction

# Деньги храним с точностью до копеек
MONEY_QUANTUM = Decimal("0.01")


class PortfolioError(Exception):
    """Ошибка выполнения операции с виртуальным портфелем"""


def to_money(value: Decimal) -> Decimal:
    """Округлить сумму до двух знаков (математическое округление)"""
    return value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def get_or_create_portfolio(user) -> Portfolio:
    """Получить портфель пользователя, создав его при необходимости"""
    portfolio, _ = Portfolio.objects.get_or_create(user=user)
    return portfolio


def _validate_quantity(quantity: int) -> int:
    try:
        quantity = int(quantity)
    except (TypeError, ValueError) as error:
        raise PortfolioError("Количество акций должно быть целым числом.") from error
    if quantity <= 0:
        raise PortfolioError("Количество акций должно быть больше нуля.")
    return quantity


def _get_trade_price(share: Share) -> Decimal:
    if share.last_price is None:
        raise PortfolioError(f"Для акции {share.ticker} не задана текущая цена.")
    # Decimal(str(...)) корректно переводит и Decimal, и float в Decimal
    return Decimal(str(share.last_price))


@transaction.atomic
def buy_share(user, share: Share, quantity: int) -> Portfolio:
    """
    Покупка акций: списывает сумму со баланса, создает/обновляет позицию
    (с пересчетом средней цены) и фиксирует сделку.
    """
    quantity = _validate_quantity(quantity)
    price = _get_trade_price(share)

    portfolio = get_or_create_portfolio(user)
    # Блокируем строку портфеля до конца транзакции
    portfolio = Portfolio.objects.select_for_update().get(pk=portfolio.pk)

    total_amount = to_money(price * quantity)
    if total_amount > portfolio.balance:
        raise PortfolioError("Недостаточно средств на балансе портфеля.")

    portfolio.balance = to_money(portfolio.balance - total_amount)
    portfolio.save(update_fields=["balance", "updated_at"])

    position = (
        PortfolioPosition.objects.select_for_update()
        .filter(portfolio=portfolio, share=share)
        .first()
    )
    if position is None:
        position = PortfolioPosition.objects.create(
            portfolio=portfolio,
            share=share,
            quantity=quantity,
            average_price=to_money(price),
        )
    else:
        total_quantity = position.quantity + quantity
        # Пересчет средней цены: (old_qty * old_avg + new_qty * price) / total_qty
        position.average_price = to_money(
            (position.average_price * position.quantity + price * quantity)
            / Decimal(total_quantity)
        )
        position.quantity = total_quantity
        position.save(update_fields=["quantity", "average_price", "updated_at"])

    Transaction.objects.create(
        portfolio=portfolio,
        share=share,
        transaction_type=Transaction.TransactionType.BUY,
        quantity=quantity,
        price=price,
        total_amount=total_amount,
    )
    return portfolio


@transaction.atomic
def sell_share(user, share: Share, quantity: int) -> Portfolio:
    """
    Продажа акций: пополняет баланс, уменьшает/удаляет позицию
    и фиксирует сделку.
    """
    quantity = _validate_quantity(quantity)
    price = _get_trade_price(share)

    portfolio = get_or_create_portfolio(user)
    portfolio = Portfolio.objects.select_for_update().get(pk=portfolio.pk)

    position = (
        PortfolioPosition.objects.select_for_update()
        .filter(portfolio=portfolio, share=share)
        .first()
    )
    if position is None or position.quantity < quantity:
        available = position.quantity if position else 0
        raise PortfolioError(
            f"Недостаточно акций для продажи (в наличии: {available})."
        )

    total_amount = to_money(price * quantity)
    portfolio.balance = to_money(portfolio.balance + total_amount)
    portfolio.save(update_fields=["balance", "updated_at"])

    if position.quantity == quantity:
        # При полной продаже позиция удаляется
        position.delete()
    else:
        position.quantity -= quantity
        position.save(update_fields=["quantity", "updated_at"])

    Transaction.objects.create(
        portfolio=portfolio,
        share=share,
        transaction_type=Transaction.TransactionType.SELL,
        quantity=quantity,
        price=price,
        total_amount=total_amount,
    )
    return portfolio


def get_portfolio_summary(portfolio: Portfolio) -> dict:
    """
    Сводка по портфелю: баланс, стоимость позиций, общая стоимость
    и общий/позиционный PnL.
    """
    positions = list(portfolio.positions.select_related("share"))
    positions_value = sum((position.current_value for position in positions), Decimal("0.00"))
    total_value = to_money(portfolio.balance + positions_value)
    total_pnl = to_money(total_value - INITIAL_BALANCE)
    return {
        "portfolio": portfolio,
        "positions": positions,
        "balance": portfolio.balance,
        "positions_value": to_money(positions_value),
        "total_value": total_value,
        "total_pnl": total_pnl,
    }
