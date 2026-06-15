from decimal import Decimal

from domain.commands import PlaceBuyLimitCommand
from domain.enums import GridLevelStatus
from strategy.grid_engine import GridEngine, GridEngineConfig, GridLevel


def test_grid_engine_activates_trailing_entry_when_price_reaches_level() -> None:
    grid = GridEngine(
        instrument_id="SBER",
        levels=[
            GridLevel(
                index=1,
                price=Decimal("300"),
            )
        ],
        config=GridEngineConfig(
            quantity=1,
            entry_rebound_percent=Decimal("0.15"),
            entry_limit_offset_percent=Decimal("0.15"),
        ),
    )

    commands = grid.on_price(
        current_price=Decimal("300"),
    )

    level = grid.levels[0]

    assert commands == []
    assert level.status == GridLevelStatus.TRAILING_ENTRY
    assert level.trailing_entry is not None
    assert level.trailing_entry.lowest_price == Decimal("300")


def test_grid_engine_moves_trailing_entry_down_and_buys_after_rebound() -> None:
    grid = GridEngine(
        instrument_id="SBER",
        levels=[
            GridLevel(
                index=1,
                price=Decimal("300"),
            )
        ],
        config=GridEngineConfig(
            quantity=1,
            entry_rebound_percent=Decimal("0.15"),
            entry_limit_offset_percent=Decimal("0.15"),
        ),
    )

    assert grid.on_price(Decimal("300")) == []

    level = grid.levels[0]
    assert level.trailing_entry is not None
    assert level.trailing_entry.lowest_price == Decimal("300")

    assert grid.on_price(Decimal("298")) == []

    level = grid.levels[0]
    assert level.trailing_entry is not None
    assert level.trailing_entry.lowest_price == Decimal("298")

    rebound_price = Decimal("298") * Decimal("1.0015")

    commands = grid.on_price(
        current_price=rebound_price,
    )

    assert len(commands) == 1
    assert isinstance(commands[0], PlaceBuyLimitCommand)

    expected_buy_price = rebound_price * Decimal("1.0015")

    assert commands[0].instrument_id == "SBER"
    assert commands[0].level_index == 1
    assert commands[0].quantity == 1
    assert commands[0].price == expected_buy_price

    assert level.status == GridLevelStatus.ORDER_PLACED


def test_grid_engine_does_not_buy_before_rebound() -> None:
    grid = GridEngine(
        instrument_id="SBER",
        levels=[
            GridLevel(
                index=1,
                price=Decimal("300"),
            )
        ],
        config=GridEngineConfig(
            quantity=1,
            entry_rebound_percent=Decimal("0.15"),
            entry_limit_offset_percent=Decimal("0.15"),
        ),
    )

    assert grid.on_price(Decimal("300")) == []
    assert grid.on_price(Decimal("298")) == []

    price_before_rebound = Decimal("298") * Decimal("1.0014")

    commands = grid.on_price(
        current_price=price_before_rebound,
    )

    assert commands == []
