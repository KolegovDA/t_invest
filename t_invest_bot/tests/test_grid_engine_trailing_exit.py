from decimal import Decimal

from domain.commands import PlaceSellLimitCommand
from domain.events import TradeExecutedEvent
from strategy.grid_engine import GridEngine, GridEngineConfig, GridLevel

from domain.commands import (
    PlaceBuyLimitCommand,
    PlaceSellLimitCommand,
)

def test_grid_engine_activates_trailing_exit_after_take_profit_but_does_not_sell_immediately() -> None:
    grid = GridEngine(
        instrument_id="SBER",
        levels=[
            GridLevel(
                index=1,
                price=Decimal("324"),
            )
        ],
        config=GridEngineConfig(
            quantity=1,
            min_profit_percent=Decimal("0.30"),
            take_profit_buffer_percent=Decimal("0.15"),
            trailing_percent=Decimal("0.50"),
        ),
    )

    grid.on_trade_executed(
        event=TradeExecutedEvent(
            instrument_id="SBER",
            level_index=1,
            side="BUY",
            quantity=1,
            price=Decimal("324"),
            commission=None,
        )
    )

    commands = grid.on_price(
        current_price=Decimal("331"),
    )

    position = grid.open_positions[1]

    assert commands == []
    assert position.trailing_exit is not None
    assert position.trailing_exit.highest_price == Decimal("331")


def test_grid_engine_moves_trailing_exit_up_and_sells_after_rollback() -> None:
    grid = GridEngine(
        instrument_id="SBER",
        levels=[
            GridLevel(
                index=1,
                price=Decimal("324"),
            )
        ],
        config=GridEngineConfig(
            quantity=1,
            min_profit_percent=Decimal("0.30"),
            take_profit_buffer_percent=Decimal("0.15"),
            trailing_percent=Decimal("0.50"),
            exit_limit_offset_percent=Decimal("0.15"),
        ),
    )

    grid.on_trade_executed(
        event=TradeExecutedEvent(
            instrument_id="SBER",
            level_index=1,
            side="BUY",
            quantity=1,
            price=Decimal("324"),
            commission=None,
        )
    )

    assert grid.on_price(Decimal("331")) == []

    position = grid.open_positions[1]
    assert position.trailing_exit is not None
    assert position.trailing_exit.highest_price == Decimal("331")

    assert grid.on_price(Decimal("333")) == []

    position = grid.open_positions[1]
    assert position.trailing_exit is not None
    assert position.trailing_exit.highest_price == Decimal("333")

    rollback_price = Decimal("333") * Decimal("0.995")

    commands = grid.on_price(
        current_price=rollback_price,
    )

    assert len(commands) == 1
    assert isinstance(commands[0], PlaceSellLimitCommand)
    assert commands[0].instrument_id == "SBER"
    assert commands[0].level_index == 1
    assert commands[0].quantity == 1
    assert commands[0].price >= grid.open_positions[1].hard_take_profit_price


def test_grid_engine_uses_fallback_commission_when_actual_commission_is_missing() -> None:
    grid = GridEngine(
        instrument_id="SBER",
        levels=[
            GridLevel(
                index=1,
                price=Decimal("324"),
            )
        ],
        config=GridEngineConfig(
            quantity=1,
            fallback_buy_commission_percent=Decimal("0.30"),
            fallback_sell_commission_percent=Decimal("0.30"),
        ),
    )

    grid.on_trade_executed(
        event=TradeExecutedEvent(
            instrument_id="SBER",
            level_index=1,
            side="BUY",
            quantity=1,
            price=Decimal("324"),
            commission=None,
        )
    )

    position = grid.open_positions[1]

    assert position.buy_commission == Decimal("0.972")

    grid.on_trade_executed(
        event=TradeExecutedEvent(
            instrument_id="SBER",
            level_index=1,
            side="SELL",
            quantity=1,
            price=Decimal("330"),
            commission=None,
        )
    )

    expected_profit = (
        Decimal("330")
        - Decimal("0.99")
        - Decimal("324")
        - Decimal("0.972")
    )

    assert grid.open_positions == {}
    assert grid.realized_profit == expected_profit

def test_sell_limit_is_below_current_price_after_trailing() -> None:
    grid = GridEngine(
        instrument_id="SBER",
        levels=[
            GridLevel(
                index=1,
                price=Decimal("324"),
            )
        ],
        config=GridEngineConfig(
            quantity=1,
            min_profit_percent=Decimal("0.30"),
            take_profit_buffer_percent=Decimal("0.15"),
            trailing_percent=Decimal("0.50"),
            exit_limit_offset_percent=Decimal("0.15"),
        ),
    )

    grid.on_trade_executed(
        TradeExecutedEvent(
            instrument_id="SBER",
            level_index=1,
            side="BUY",
            quantity=1,
            price=Decimal("324"),
            commission=None,
        )
    )

    position = grid.open_positions[1]

    activation_price = (
        grid._calculate_exit_activation_price(
            position.hard_take_profit_price
        )
    )

    assert (
        grid.on_price(
            activation_price
        )
        == []
    )

    rollback_price = (
        activation_price
        * Decimal("0.995")
    )

    commands = grid.on_price(
        rollback_price
    )

    assert len(commands) == 1

    command = commands[0]

    assert isinstance(
        command,
        PlaceSellLimitCommand,
    )

    assert (
        command.price
        < rollback_price
    )

    assert (
        command.price
        >= position.hard_take_profit_price
    )


def test_sell_order_is_created_only_once_while_waiting_for_execution() -> None:
    grid = GridEngine(
        instrument_id="SBER",
        levels=[
            GridLevel(
                index=1,
                price=Decimal("324"),
            )
        ],
        config=GridEngineConfig(
            quantity=1,
            min_profit_percent=Decimal("0.30"),
            take_profit_buffer_percent=Decimal("0.15"),
            trailing_percent=Decimal("0.50"),
            exit_limit_offset_percent=Decimal("0.15"),
        ),
    )

    grid.on_trade_executed(
        TradeExecutedEvent(
            instrument_id="SBER",
            level_index=1,
            side="BUY",
            quantity=1,
            price=Decimal("324"),
            commission=None,
        )
    )

    position = grid.open_positions[1]

    activation_price = (
        grid._calculate_exit_activation_price(
            position.hard_take_profit_price
        )
    )

    grid.on_price(
        activation_price
    )

    rollback_price = (
        activation_price
        * Decimal("0.995")
    )

    first_commands = grid.on_price(
        rollback_price
    )

    assert len(first_commands) == 1

    second_commands = grid.on_price(
        rollback_price
    )

    third_commands = grid.on_price(
        rollback_price
    )

    assert second_commands == []
    assert third_commands == []


def test_buy_limit_is_above_current_price_after_entry_trailing() -> None:
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

    assert (
        grid.on_price(
            Decimal("300")
        )
        == []
    )

    assert (
        grid.on_price(
            Decimal("298")
        )
        == []
    )

    rebound_price = (
        Decimal("298")
        * Decimal("1.0015")
    )

    commands = grid.on_price(
        rebound_price
    )

    assert len(commands) == 1

    command = commands[0]

    assert isinstance(
        command,
        PlaceBuyLimitCommand,
    )

    assert (
        command.price
        > rebound_price
    )
