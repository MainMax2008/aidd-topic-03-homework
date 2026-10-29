from decimal import Decimal

from tinkoff.invest import Client

from config.settings import TINKOFF_TOKEN, logger


def get_last_data(share):
    with Client(TINKOFF_TOKEN) as client:
        resp = client.market_data.get_last_prices(figi=[share.figi])
        last_prices = list(resp.last_prices)
        if not last_prices:
            logger.error("No last prices for share %s", share.id)
            return None
        price_obj = last_prices[0]
        logger.info("Get last data for share with id %s", share.id)
        # units + nano для сохранения точности (nano = 1e-9 от единицы)
        price = Decimal(str(price_obj.price.units)) + Decimal(
            str(price_obj.price.nano)
        ) / Decimal(1_000_000_000)
        return [price, price_obj.time]
