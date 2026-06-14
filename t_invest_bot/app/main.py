from datetime import datetime, timedelta
from decimal import Decimal

from domain.entities import Candle
from strategy.grid_builder import GridBuilder
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

    analyzer = HistoryAnalyzer(exclude_first_days=7)
    price_range = analyzer.calculate_range(candles)

    print(price_range)

    builder = GridBuilder(levels_count=5)

    levels = builder.build_from_range(
        min_price=price_range.min_price,
        max_price=price_range.max_price,
    )

    for level in levels:
        print(level)


if __name__ == "__main__":
    main()
