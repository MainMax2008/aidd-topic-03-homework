from config.celery import app
from dashboard.models import Share
from dashboard.services.market_data import get_last_data
from config.settings import logger


@app.task
def update_last_price():
    shares = Share.objects.all()

    for share in shares:
        try:
            result = get_last_data(share)
            if result is None:
                logger.error("No price data for share %s", share.id)
                continue

            last_price, updated_at = result

            # None-check: если предыдущей цены нет, считаем тренд растущим
            if share.last_price is None:
                is_trend_high = True
            elif last_price > share.last_price:
                is_trend_high = True
            else:
                is_trend_high = False

            Share.objects.filter(id=share.id).update(
                last_price=last_price, is_trend_high=is_trend_high, updated_at=updated_at
            )
        except Exception as e:
            logger.error("Error updating price for share %s: %s", share.id, e)
