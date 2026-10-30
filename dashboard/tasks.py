from config.celery import app
from dashboard.models import Share
from dashboard.services.market_data import get_last_data
from config.settings import logger


@app.task
def update_last_price():
    shares = Share.objects.all()

    for share in shares:
        try:
            last_data = get_last_data(share)
            if last_data is None:
                continue

            last_price, price_timestamp = last_data
            is_trend_high = share.last_price is None or last_price >= share.last_price

            Share.objects.filter(id=share.id).update(
                last_price=last_price,
                is_trend_high=is_trend_high,
                updated_at=price_timestamp,
            )
        except Exception as e:
            logger.error(e)
