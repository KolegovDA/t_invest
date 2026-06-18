from datetime import datetime
from decimal import Decimal

from domain.entities import Candle
from strategy.grid_builder import GridBuilder
from strategy.history_analyzer import HistoryAnalyzer


def test_history_analyzer_excludes_first_days() -> None:
    candles = [
        Candle(
            instrument_id="SBER",
            open=Decimal("100"),
            high=Decimal("1000"),
            low=Decimal("10"),
            close=Decimal("100"),
            volume=1000,
            timestamp=datetime(2024, 1, 1),
        ),
        Candle(
            instrument_id="SBER",
            open=Decimal("100"),
            high=Decimal("200"),
            low=Decimal("90"),
            close=Decimal("100"),
            volume=1000,
            timestamp=datetime(2024, 1, 10),
        ),
    ]

    price_range = HistoryAnalyzer(
        exclude_first_days=7,
    ).calculate_range(
        candles=candles,
    )

    assert price_range.min_price == Decimal("90")
    assert price_range.max_price == Decimal("200")


def test_grid_builder_builds_levels_from_current_price_to_min_with_growing_steps() -> None:
    builder = GridBuilder(
        levels_count=5,
    )

    levels = builder.build_from_range(
        min_price=Decimal("250"),
        current_price=Decimal("300"),
    )

    assert len(levels) == 5

    assert levels[0].price < Decimal("300")
    assert levels[-1].price == Decimal("250")

    steps = [
        Decimal("300") - levels[0].price,
        levels[0].price - levels[1].price,
        levels[1].price - levels[2].price,
        levels[2].price - levels[3].price,
        levels[3].price - levels[4].price,
    ]

    assert steps[0] >= Decimal("300") * Decimal("0.0015")
    assert steps[1] > steps[0]
    assert steps[2] > steps[1]
    assert steps[3] > steps[2]
    assert steps[4] > steps[3]


def test_grid_builder_continues_below_min_price_when_range_is_too_narrow() -> None:
    builder = GridBuilder(
        levels_count=20,
    )

    levels = builder.build_from_range(
        min_price=Decimal("99"),
        current_price=Decimal("100"),
    )

    assert len(levels) == 20
    assert levels[0].price == Decimal("99.8500")
    assert levels[-1].price < Decimal("99")

    steps = [
        Decimal("100") - levels[0].price,
    ]

    for index in range(1, len(levels)):
        steps.append(
            levels[index - 1].price - levels[index].price
        )

    assert steps[0] == Decimal("0.1500")
    assert steps[1] > steps[0]
    assert steps[2] > steps[1]


def test_grid_builder_rejects_invalid_levels_count() -> None:
    builder = GridBuilder(
        levels_count=0,
    )

    try:
        builder.build_from_range(
            min_price=Decimal("250"),
            current_price=Decimal("300"),
        )
    except ValueError as error:
        assert str(error) == "levels_count must be greater than zero"
    else:
        raise AssertionError("ValueError was not raised")
