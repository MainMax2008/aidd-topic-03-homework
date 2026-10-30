from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction

from dashboard.models import Portfolio, PortfolioTransaction, Position, Share

CENT = Decimal("0.01")


def _get_price(share):
    if share.currency.lower() not in ("rub", "rur"):
        raise ValidationError(
            "Портфель ведется в рублях; сделки в другой валюте пока не поддерживаются."
        )
    if share.last_price is None:
        raise ValidationError("Для этой акции пока нет актуальной рыночной цены.")

    try:
        price = Decimal(str(share.last_price)).quantize(CENT)
    except (InvalidOperation, ValueError):
        raise ValidationError("Текущая цена акции некорректна.") from None

    if not price.is_finite() or price <= 0:
        raise ValidationError("Текущая цена акции должна быть положительной.")
    return price


def _validate_quantity(quantity):
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
        raise ValidationError("Количество акций должно быть положительным целым числом.")


def _get_share(share_id):
    try:
        return Share.objects.get(pk=share_id)
    except Share.DoesNotExist:
        raise ValidationError("Акция не найдена.") from None


def buy_share(user, share_id, quantity):
    _validate_quantity(quantity)

    with transaction.atomic():
        portfolio, _ = Portfolio.objects.get_or_create(user=user)
        portfolio = Portfolio.objects.select_for_update().get(pk=portfolio.pk)
        share = _get_share(share_id)
        price = _get_price(share)
        total_cost = price * quantity

        if portfolio.balance < total_cost:
            raise ValidationError("Недостаточно средств для покупки.")

        position = (
            Position.objects.select_for_update()
            .filter(portfolio=portfolio, share=share)
            .first()
        )
        if position:
            total_quantity = position.quantity + quantity
            weighted_cost = (
                position.average_buy_price * position.quantity + price * quantity
            )
            position.quantity = total_quantity
            position.average_buy_price = (weighted_cost / total_quantity).quantize(CENT)
            position.save(update_fields=("quantity", "average_buy_price"))
        else:
            Position.objects.create(
                portfolio=portfolio,
                share=share,
                quantity=quantity,
                average_buy_price=price,
            )

        portfolio.balance -= total_cost
        portfolio.save(update_fields=("balance",))
        return PortfolioTransaction.objects.create(
            portfolio=portfolio,
            share=share,
            transaction_type=PortfolioTransaction.Type.BUY,
            quantity=quantity,
            price=price,
        )


def sell_share(user, share_id, quantity):
    _validate_quantity(quantity)

    with transaction.atomic():
        portfolio, _ = Portfolio.objects.get_or_create(user=user)
        portfolio = Portfolio.objects.select_for_update().get(pk=portfolio.pk)
        share = _get_share(share_id)
        price = _get_price(share)
        position = (
            Position.objects.select_for_update()
            .filter(portfolio=portfolio, share=share)
            .first()
        )

        if position is None or position.quantity < quantity:
            raise ValidationError("Недостаточно акций для продажи.")

        position.quantity -= quantity
        if position.quantity:
            position.save(update_fields=("quantity",))
        else:
            position.delete()

        portfolio.balance += price * quantity
        portfolio.save(update_fields=("balance",))
        return PortfolioTransaction.objects.create(
            portfolio=portfolio,
            share=share,
            transaction_type=PortfolioTransaction.Type.SELL,
            quantity=quantity,
            price=price,
        )


def get_portfolio_summary(user):
    portfolio, _ = Portfolio.objects.get_or_create(user=user)
    positions = []
    market_value = Decimal("0.00")
    invested_value = Decimal("0.00")
    total_pnl = Decimal("0.00")
    unpriced_positions = 0

    for position in portfolio.positions.select_related("share").all():
        share = position.share
        current_price = None
        position_value = None
        position_pnl = None
        position_pnl_percent = None

        try:
            current_price = _get_price(share)
        except ValidationError:
            unpriced_positions += 1
        else:
            position_value = (current_price * position.quantity).quantize(CENT)
            position_cost = (position.average_buy_price * position.quantity).quantize(CENT)
            position_pnl = position_value - position_cost
            position_pnl_percent = (
                (position_pnl / position_cost * 100).quantize(CENT)
                if position_cost
                else Decimal("0.00")
            )
            market_value += position_value
            invested_value += position_cost
            total_pnl += position_pnl

        positions.append(
            {
                "position": position,
                "share": share,
                "quantity": position.quantity,
                "average_buy_price": position.average_buy_price,
                "current_price": current_price,
                "market_value": position_value,
                "pnl": position_pnl,
                "pnl_percent": position_pnl_percent,
            }
        )

    total_pnl_percent = (
        (total_pnl / invested_value * 100).quantize(CENT)
        if invested_value
        else Decimal("0.00")
    )
    return {
        "portfolio": portfolio,
        "balance": portfolio.balance,
        "market_value": market_value.quantize(CENT),
        "total_assets": (portfolio.balance + market_value).quantize(CENT),
        "total_pnl": total_pnl.quantize(CENT),
        "total_pnl_percent": total_pnl_percent,
        "prices_complete": unpriced_positions == 0,
        "unpriced_positions": unpriced_positions,
        "positions": positions,
        "transactions": portfolio.transactions.select_related("share")[:10],
    }
