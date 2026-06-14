from datetime import datetime, timedelta
from decimal import Decimal

from domain.entities import Candle
from strategy.grid_engine import GridEngineConfig
from strategy.grid_factory import GridFactory
from strategy.history_analyzer import HistoryAnalyzer


def main() -> None:
    start = datetime(2024, 1, 1)

    candles = []

    for i in range(20):
        candles.append(
            Candle(
                instrument_id="SBER",
                open=Decimal("100") + Decimal(i),
                high=Decimal("110") + Decimal(i),
                low=Decimal("90") + Decimal(i),
                close=Decimal("100") + Decimal(i),
                volume=1000,
                timestamp=start + timedelta(days=i),
            )
        )

    factory = GridFactory(
        history_analyzer=HistoryAnalyzer(exclude_first_days=7),
    )

    result = factory.create_grid_engine(
        instrument_id="SBER",
        candles=candles,
        levels_count=5,
        config=GridEngineConfig(quantity=10),
    )

    print(result.price_range)

    for level in result.grid_engine.levels:
        print(level)


if __name__ == "__main__":
    main()
