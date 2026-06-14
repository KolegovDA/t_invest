from dataclasses import dataclass, field
from decimal import Decimal

from broker.live_order_manager import LiveOrderManager
from domain.order_execution import PlacedOrder
from strategy.grid_engine import GridEngine


@dataclass(slots=True)
class SandboxTradingSession:
    grid_engine: GridEngine
    live_order_manager: LiveOrderManager
    placed_orders: list[PlacedOrder] = field(default_factory=list)

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

    def stop(self) -> None:
        self.live_order_manager.cancel_all_orders()
