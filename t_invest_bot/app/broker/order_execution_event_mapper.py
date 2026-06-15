from dataclasses import dataclass

from broker.order_state_tracker import ExecutedOrder
from domain.commands import (
    PlaceBuyLimitCommand,
    PlaceSellAllLimitCommand,
    PlaceSellLimitCommand,
)
from domain.events import TradeExecutedEvent


@dataclass(slots=True)
class OrderExecutionEventMapper:
    def map_to_trade_event(
        self,
        executed_order: ExecutedOrder,
    ) -> TradeExecutedEvent:
        command = executed_order.order_record.command
        state = executed_order.execution_state

        if state.executed_price is None:
            raise ValueError("Executed price is missing")

        if isinstance(command, PlaceBuyLimitCommand):
            return TradeExecutedEvent(
                instrument_id=command.instrument_id,
                level_index=command.level_index,
                side="BUY",
                quantity=state.executed_quantity,
                price=state.executed_price,
                commission=None,
            )

        if isinstance(command, PlaceSellLimitCommand):
            return TradeExecutedEvent(
                instrument_id=command.instrument_id,
                level_index=command.level_index,
                side="SELL",
                quantity=state.executed_quantity,
                price=state.executed_price,
                commission=None,
            )

        if isinstance(command, PlaceSellAllLimitCommand):
            return TradeExecutedEvent(
                instrument_id=command.instrument_id,
                level_index=0,
                side="SELL",
                quantity=state.executed_quantity,
                price=state.executed_price,
                commission=None,
            )

        raise ValueError(
            f"Unsupported command type: {type(command)}"
        )
