from config.settings import TINKOFF_TOKEN, logger


def get_last_data(share):
    from tinkoff.invest import Client

    with Client(TINKOFF_TOKEN) as client:
        resp = client.market_data.get_last_prices(figi=[share.figi])
        if resp is None or not resp.last_prices:
            return None

        price = resp.last_prices.pop().price
        if price is None:
            return None

        logger.info(f"Get last data for share with id {share.id}")
        return [price.units + price.nano / 10**9, resp.time]
