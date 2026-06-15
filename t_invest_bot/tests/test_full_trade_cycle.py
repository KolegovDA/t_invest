from decimal import Decimal

from domain.commands import PlaceSellLimitCommand
from domain.events import TradeExecutedEvent
from strategy.grid_engine import (
    GridEngine,
    GridEngineConfig,
    GridLevel,
)


def test_full_trade_cycle() -> None:
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
            trailing_percent=Decimal("0.50"),
            min_profit_percent=Decimal("0.30"),
            take_profit_buffer_percent=Decimal("0.15"),
            fallback_buy_commission_percent=Decimal("0.30"),
            fallback_sell_commission_percent=Decimal("0.30"),
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

    assert len(grid.open_positions) == 1

    assert grid.on_price(
        Decimal("331")
    ) == []

    assert grid.on_price(
        Decimal("333")
    ) == []

    sell_commands = grid.on_price(
        Decimal("331.30")
    )

    assert len(sell_commands) == 1

    sell_command = sell_commands[0]

    assert isinstance(
        sell_command,
        PlaceSellLimitCommand,
    )

    grid.on_trade_executed(
        TradeExecutedEvent(
            instrument_id="SBER",
            level_index=1,
            side="SELL",
            quantity=1,
            price=sell_command.price,
            commission=None,
        )
    )

    assert grid.open_positions == {}

    assert grid.realized_profit > 0
