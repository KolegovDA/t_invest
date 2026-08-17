from datetime import datetime
from decimal import Decimal

from domain.entities import Candle
from strategy.grid_builder import (
    GridBuilder,
)
from strategy.history_analyzer import (
    HistoryAnalyzer,
)


def test_history_analyzer_excludes_first_week(
) -> None:
    candles = [
        Candle(
            instrument_id="SBER",
            open=Decimal("100"),
            high=Decimal("1000"),
            low=Decimal("10"),
            close=Decimal("100"),
            volume=1000,
            timestamp=datetime(
                2024,
                1,
                1,
            ),
        ),
        Candle(
            instrument_id="SBER",
            open=Decimal("100"),
            high=Decimal("200"),
            low=Decimal("90"),
            close=Decimal("100"),
            volume=1000,
            timestamp=datetime(
                2024,
                1,
                10,
            ),
        ),
    ]

    price_range = (
        HistoryAnalyzer(
            exclude_first_days=7,
        )
        .calculate_range(
            candles=candles,
        )
    )

    assert (
        price_range.min_price
        == Decimal("90")
    )

    assert (
        price_range.max_price
        == Decimal("200")
    )


def test_grid_builder_uses_equal_steps_from_current_price_to_min(
) -> None:
    builder = (
        GridBuilder(
            levels_count=5,
        )
    )

    levels = (
        builder.build_from_range(
            min_price=Decimal("250"),
            current_price=Decimal("300"),
        )
    )

    #
    # Диапазон:
    #
    # 300 - 250 = 50
    #
    # 50 / 5 = 10
    #
    assert len(levels) == 5

    assert (
        levels[0].price
        == Decimal("290")
    )

    assert (
        levels[1].price
        == Decimal("280")
    )

    assert (
        levels[2].price
        == Decimal("270")
    )

    assert (
        levels[3].price
        == Decimal("260")
    )

    assert (
        levels[4].price
        == Decimal("250")
    )


def test_grid_builder_uses_minimum_step_of_point_three_percent(
) -> None:
    builder = (
        GridBuilder(
            levels_count=20,
        )
    )

    levels = (
        builder.build_from_range(
            min_price=Decimal("99"),
            current_price=Decimal("100"),
        )
    )

    #
    # Исторический шаг:
    #
    # (100 - 99) / 20 = 0.05
    #
    # Минимальный:
    #
    # 100 × 0.30% = 0.30
    #
    # Значит используем 0.30.
    #
    assert len(levels) == 20

    assert (
        levels[0].price
        == Decimal("99.70")
    )

    assert (
        levels[1].price
        == Decimal("99.40")
    )

    assert (
        levels[2].price
        == Decimal("99.10")
    )

    assert (
        levels[-1].price
        == Decimal("94.00")
    )


def test_grid_builder_step_is_constant(
) -> None:
    builder = (
        GridBuilder(
            levels_count=10,
        )
    )

    levels = (
        builder.build_from_range(
            min_price=Decimal("70"),
            current_price=Decimal("100"),
        )
    )

    steps = [
        (
            Decimal("100")
            - levels[0].price
        )
    ]

    for index in range(
        1,
        len(levels),
    ):
        steps.append(
            levels[
                index - 1
            ].price
            - levels[
                index
            ].price
        )

    assert all(
        step
        == Decimal("3")
        for step
        in steps
    )


def test_grid_builder_can_continue_below_historical_min(
) -> None:
    builder = (
        GridBuilder(
            levels_count=20,
        )
    )

    levels = (
        builder.build_from_range(
            min_price=Decimal("99"),
            current_price=Decimal("100"),
        )
    )

    #
    # Из-за minimum step 0.30%
    # двадцатый уровень уйдёт
    # ниже исторического минимума.
    #
    assert (
        levels[-1].price
        < Decimal("99")
    )


def test_grid_builder_works_when_current_price_is_below_historical_min(
) -> None:
    builder = (
        GridBuilder(
            levels_count=10,
        )
    )

    levels = (
        builder.build_from_range(
            min_price=Decimal("101"),
            current_price=Decimal("100"),
        )
    )

    #
    # Рынок сделал новый минимум.
    #
    # Историческая дистанция = 0,
    # используем минимальный
    # шаг 0.30%.
    #
    assert (
        levels[0].price
        == Decimal("99.70")
    )

    assert (
        levels[1].price
        == Decimal("99.40")
    )


def test_calculate_step_returns_historical_step(
) -> None:
    builder = (
        GridBuilder(
            levels_count=20,
        )
    )

    step = builder.calculate_step(
        min_price=Decimal("70"),
        current_price=Decimal("100"),
    )

    assert (
        step
        == Decimal("1.5")
    )


def test_calculate_step_returns_minimum_step(
) -> None:
    builder = (
        GridBuilder(
            levels_count=20,
        )
    )

    step = builder.calculate_step(
        min_price=Decimal("99"),
        current_price=Decimal("100"),
    )

    assert (
        step
        == Decimal("0.30")
    )


def test_grid_builder_rejects_invalid_levels_count(
) -> None:
    builder = (
        GridBuilder(
            levels_count=0,
        )
    )

    try:
        builder.build_from_range(
            min_price=Decimal("250"),
            current_price=Decimal("300"),
        )

    except ValueError as error:
        assert (
            str(error)
            == (
                "levels_count must be "
                "greater than zero"
            )
        )

    else:
        raise AssertionError(
            "ValueError was not raised"
        )
