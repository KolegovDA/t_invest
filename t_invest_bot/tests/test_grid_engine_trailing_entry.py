from decimal import Decimal

from domain.commands import (
    PlaceBuyLimitCommand,
)
from domain.enums import (
    GridLevelStatus,
)
from strategy.grid_engine import (
    GridEngine,
    GridEngineConfig,
    GridLevel,
)


def create_grid(
) -> GridEngine:
    return GridEngine(
        instrument_id="SBER",

        levels=[
            GridLevel(
                index=1,
                price=Decimal("99"),
            )
        ],

        config=GridEngineConfig(
            quantity=1,

            first_entry_activation_percent=(
                Decimal("0.50")
            ),

            entry_rebound_percent=(
                Decimal("0.15")
            ),

            entry_limit_offset_percent=(
                Decimal("0.15")
            ),
        ),

        session_start_price=(
            Decimal("100")
        ),

        grid_step=(
            Decimal("1")
        ),
    )


def test_grid_engine_does_not_activate_before_half_percent(
) -> None:
    grid = create_grid()

    commands = grid.on_price(
        Decimal("100.49")
    )

    level = grid.levels[0]

    assert commands == []

    assert (
        level.status
        == GridLevelStatus
        .WAITING_PRICE
    )

    assert (
        level.trailing_entry
        is None
    )


def test_grid_engine_activates_trailing_entry_on_positive_half_percent(
) -> None:
    grid = create_grid()

    commands = grid.on_price(
        Decimal("100.50")
    )

    level = grid.levels[0]

    assert commands == []

    assert (
        level.status
        == GridLevelStatus
        .TRAILING_ENTRY
    )

    assert (
        level.trailing_entry
        is not None
    )

    assert (
        level
        .trailing_entry
        .highest_price
        == Decimal("100.50")
    )


def test_grid_engine_activates_trailing_entry_on_negative_half_percent(
) -> None:
    grid = create_grid()

    commands = grid.on_price(
        Decimal("99.50")
    )

    assert commands == []

    level = grid.levels[0]

    assert (
        level.status
        == GridLevelStatus
        .TRAILING_ENTRY
    )

    assert (
        level.trailing_entry
        is not None
    )

    assert (
        level
        .trailing_entry
        .highest_price
        == Decimal("99.50")
    )


def test_grid_engine_moves_trailing_up_with_every_new_high(
) -> None:
    grid = create_grid()

    grid.on_price(
        Decimal("100.50")
    )

    grid.on_price(
        Decimal("100.60")
    )

    level = grid.levels[0]

    assert (
        level.trailing_entry
        is not None
    )

    assert (
        level
        .trailing_entry
        .highest_price
        == Decimal("100.60")
    )

    expected_trigger = (
        Decimal("100.60")
        * Decimal("0.9985")
    )

    assert (
        level
        .trailing_entry
        .trigger_price
        == expected_trigger
    )


def test_grid_engine_places_buy_after_trailing_touch(
) -> None:
    grid = create_grid()

    grid.on_price(
        Decimal("100.50")
    )

    grid.on_price(
        Decimal("101")
    )

    level = grid.levels[0]

    assert (
        level.trailing_entry
        is not None
    )

    trigger_price = (
        level
        .trailing_entry
        .trigger_price
    )

    assert (
        trigger_price
        is not None
    )

    commands = grid.on_price(
        trigger_price
    )

    assert (
        len(commands)
        == 1
    )

    assert isinstance(
        commands[0],
        PlaceBuyLimitCommand,
    )

    assert (
        commands[0]
        .instrument_id
        == "SBER"
    )

    assert (
        commands[0]
        .level_index
        == 1
    )

    assert (
        commands[0]
        .quantity
        == 1
    )

    assert (
        commands[0].price
        == (
            trigger_price
            * Decimal("1.0015")
        )
    )

    assert (
        level.status
        == GridLevelStatus
        .ORDER_PLACED
    )
