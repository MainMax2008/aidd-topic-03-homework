from datetime import timedelta

from plotly.graph_objs import Scatter
from plotly.offline import plot
from tinkoff.invest import CandleInterval, Client
from tinkoff.invest.utils import now

from config.settings import TINKOFF_TOKEN


def get_graph(share):
    with Client(TINKOFF_TOKEN) as client:
        x_data, y_data = [], []
        for candle in client.get_all_candles(
            figi=share.figi,
            from_=now() - timedelta(days=180),
            interval=CandleInterval.CANDLE_INTERVAL_DAY,
        ):
            x_data.append(candle.time.date())
            # units + nano для сохранения точности (nano = 1e-9 от единицы)
            y_data.append(candle.close.units + candle.close.nano / 1_000_000_000)
    plot_div = plot(
        [
            Scatter(
                x=x_data,
                y=y_data,
                mode="lines",
                name="test",
                opacity=0.8,
                marker_color="red",
            )
        ],
        output_type="div",
        show_link=False,
        link_text="",
    )
    return plot_div
