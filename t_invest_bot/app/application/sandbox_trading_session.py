from dataclasses import dataclass, field
from decimal import Decimal

from application.trade_event_handler import TradeEventHandler
from broker.live_order_manager import LiveOrderManager
from broker.order_execution_event_mapper import OrderExecutionEventMapper
from broker.order_state_tracker import OrderStateTracker
from domain.events import TradeExecutedEvent
from domain.order_execution import PlacedOrder
from strategy.grid_engine import GridEngine


@dataclass(slots=True)
class SandboxTradingSession:
    grid_engine: GridEngine
    live_order_manager: LiveOrderManager
    order_state_tracker: OrderStateTracker | None = None
    execution_event_mapper: OrderExecutionEventMapper | None = None
    trade_event_handler: TradeEventHandler | None = None
    placed_orders: list[PlacedOrder] = field(default_factory=list)
    executed_events: list[TradeExecutedEvent] = field(default_factory=list)

    def on_price(
        self,
        price: Decimal,
    ) -> list[PlacedOrder]:
        commands = self.grid_engine.on_price(
            current_price=price,
        )

        if not commands:
            return []

        placed_orders = self.live_order_manager.submit_commands(
            commands=commands,
        )

        self.placed_orders.extend(
            placed_orders,
        )

        return placed_orders

    def poll_executions(self) -> list[TradeExecutedEvent]:
        if self.order_state_tracker is None:
            return []

        if self.execution_event_mapper is None:
            return []

        executed_orders = self.order_state_tracker.poll()

        events: list[TradeExecutedEvent] = []

        for executed_order in executed_orders:
            event = self.execution_event_mapper.map_to_trade_event(
                executed_order=executed_order,
            )

            self.grid_engine.on_trade_executed(
                event=event,
            )

            if self.trade_event_handler is not None:
                self.trade_event_handler.handle(
                    event=event,
                )

            self.executed_events.append(event)
            events.append(event)

        return events

    def stop(self) -> None:
        self.live_order_manager.cancel_all_orders()
