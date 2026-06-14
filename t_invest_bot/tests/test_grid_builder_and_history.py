from datetime import datetime, timedelta
from decimal import Decimal

from domain.entities import Candle
from strategy.grid_builder import GridBuilder
from strategy.history_analyzer import HistoryAnalyzer


def test_history_analyzer_excludes_first_week_and_uses_low_high() -> None:
    start = datetime(2024, 1, 1)

    candles = []

    for i in range(20):
        candles.append(
            Candle(
                instrument_id="SBER",
                open=Decimal("100"),
                high=Decimal("110") + Decimal(i),
                low=Decimal("90") + Decimal(i),
                close=Decimal("100"),
                volume=1000,
                timestamp=start + timedelta(days=i),
            )
        )

    analyzer = HistoryAnalyzer(exclude_first_days=7)

    price_range = analyzer.calculate_range(candles)

    assert price_range.min_price == Decimal("97")
    assert price_range.max_price == Decimal("129")


def test_grid_builder_builds_levels_from_max_to_min() -> None:
    builder = GridBuilder(levels_count=5)

    levels = builder.build_from_range(
        min_price=Decimal("250"),
        max_price=Decimal("300"),
    )

    assert len(levels) == 5
    assert levels[0].price == Decimal("290")
    assert levels[1].price == Decimal("280")
    assert levels[2].price == Decimal("270")
    assert levels[3].price == Decimal("260")
    assert levels[4].price == Decimal("250")
