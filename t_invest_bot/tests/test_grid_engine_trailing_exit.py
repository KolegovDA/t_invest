from decimal import Decimal

from domain.commands import PlaceSellLimitCommand
from domain.events import TradeExecutedEvent
from strategy.grid_engine import GridEngine, GridEngineConfig, GridLevel


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
