from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404

from dashboard.models import Portfolio, PortfolioTransaction, Position, Share

CENT = Decimal("0.01")


@transaction.atomic
def get_or_create_portfolio(user):
    portfolio, _ = Portfolio.objects.get_or_create(user=user)
    return portfolio


def _get_price(share):
    if share.currency.lower() not in ("rub", "rur"):
        raise ValidationError(
            "Портфель ведется в рублях; сделки в другой валюте "
            "пока не поддерживаются."
        )
    if share.last_price is None:
        raise ValidationError(
            "Некорректная цена инструмента"
        )

    try:
        price = Decimal(str(share.last_price)).quantize(CENT)
    except (InvalidOperation, ValueError):
        raise ValidationError(
            "Некорректная цена инструмента"
        ) from None

    if not price.is_finite() or price <= 0:
        raise ValidationError(
            "Некорректная цена инструмента"
        )
    return price


def _validate_quantity(quantity):
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
        raise ValidationError(
            "Количество акций должно быть положительным целым числом."
        )


def buy_share(user, share_id, quantity):
    _validate_quantity(quantity)
    portfolio = get_or_create_portfolio(user)
    return _buy_share_atomic(user, portfolio.pk, share_id, quantity)


@transaction.atomic
def _buy_share_atomic(user, portfolio_id, share_id, quantity):
    portfolio = Portfolio.objects.select_for_update().get(pk=portfolio_id)
    share = get_object_or_404(Share, pk=share_id)
    price = _get_price(share)
    total_cost = price * quantity

    if portfolio.balance < total_cost:
        raise ValidationError(
            "Недостаточно средств для покупки."
        )

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
        total_amount=total_cost,
    )


def sell_share(user, share_id, quantity):
    _validate_quantity(quantity)
    portfolio = get_or_create_portfolio(user)
    return _sell_share_atomic(user, portfolio.pk, share_id, quantity)


@transaction.atomic
def _sell_share_atomic(user, portfolio_id, share_id, quantity):
    portfolio = Portfolio.objects.select_for_update().get(pk=portfolio_id)
    share = get_object_or_404(Share, pk=share_id)
    price = _get_price(share)
    position = (
        Position.objects.select_for_update()
        .filter(portfolio=portfolio, share=share)
        .first()
    )

    if position is None or position.quantity < quantity:
        raise ValidationError(
            "Недостаточно акций для продажи."
        )

    total_amount = price * quantity
    position.quantity -= quantity
    if position.quantity:
        position.save(update_fields=("quantity",))
    else:
        position.delete()

    portfolio.balance += total_amount
    portfolio.save(update_fields=("balance",))
    return PortfolioTransaction.objects.create(
        portfolio=portfolio,
        share=share,
        transaction_type=PortfolioTransaction.Type.SELL,
        quantity=quantity,
        price=price,
        total_amount=total_amount,
    )


def get_portfolio_summary(user):
    portfolio = get_or_create_portfolio(user)
    positions = []
    total_shares_value = Decimal("0.00")
    total_invested = Decimal("0.00")
    unpriced_positions = 0

    for position in portfolio.positions.select_related("share").all():
        share = position.share
        position_cost = (
            position.average_buy_price * position.quantity
        ).quantize(CENT)
        total_invested += position_cost

        try:
            current_price = _get_price(share)
        except ValidationError:
            current_price = None
            market_value = None
            position_pnl = None
            position_pnl_percent = None
            unpriced_positions += 1
        else:
            market_value = (current_price * position.quantity).quantize(CENT)
            position_pnl = market_value - position_cost
            position_pnl_percent = (
                (position_pnl / position_cost * 100).quantize(CENT)
                if position_cost
                else Decimal("0.00")
            )
            total_shares_value += market_value

        positions.append(
            {
                "position": position,
                "share": share,
                "quantity": position.quantity,
                "average_buy_price": position.average_buy_price,
                "current_price": current_price,
                "market_value": market_value,
                "pnl": position_pnl,
                "pnl_percent": position_pnl_percent,
            }
        )

    total_shares_value = total_shares_value.quantize(CENT)
    total_invested = total_invested.quantize(CENT)
    total_pnl = total_shares_value - total_invested
    total_pnl_percent = (
        (total_pnl / total_invested * 100).quantize(CENT)
        if total_invested
        else Decimal("0.00")
    )
    recent_transactions = portfolio.transactions.select_related("share")[:10]

    return {
        "portfolio": portfolio,
        "balance": portfolio.balance,
        "total_shares_value": total_shares_value,
        "total_portfolio_value": (
            portfolio.balance + total_shares_value
        ).quantize(CENT),
        "total_invested": total_invested,
        "total_pnl": total_pnl.quantize(CENT),
        "total_pnl_percent": total_pnl_percent,
        "prices_complete": unpriced_positions == 0,
        "unpriced_positions": unpriced_positions,
        "positions": positions,
        "recent_transactions": recent_transactions,
        # Compatibility aliases used by the existing portfolio page and API.
        "market_value": total_shares_value,
        "total_assets": (portfolio.balance + total_shares_value).quantize(CENT),
        "transactions": recent_transactions,
    }
