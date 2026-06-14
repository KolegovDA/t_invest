from dataclasses import dataclass, field

from domain.commands import (
    PlaceBuyLimitCommand,
    PlaceSellAllLimitCommand,
    PlaceSellLimitCommand,
    TradingCommand,
)
from domain.order_execution import OrderExecutor, PlacedOrder


@dataclass(slots=True)
class LiveOrderRecord:
    command: TradingCommand
    placed_order: PlacedOrder


@dataclass(slots=True)
class LiveOrderManager:
    account_id: str
    order_executor: OrderExecutor
    active_orders: dict[str, LiveOrderRecord] = field(default_factory=dict)

    def submit_commands(
        self,
        commands: list[TradingCommand],
    ) -> list[PlacedOrder]:
        placed_orders: list[PlacedOrder] = []

        for command in commands:
            placed_order = self._submit_command(
                command=command,
            )

            if placed_order is None:
                continue

            self.active_orders[placed_order.order_id] = LiveOrderRecord(
                command=command,
                placed_order=placed_order,
            )

            placed_orders.append(placed_order)

        return placed_orders

    def cancel_order(
        self,
        order_id: str,
    ) -> None:
        self.order_executor.cancel_order(
            account_id=self.account_id,
            order_id=order_id,
        )

        self.active_orders.pop(
            order_id,
            None,
        )

    def cancel_all_orders(self) -> None:
        for order_id in list(self.active_orders.keys()):
            self.cancel_order(
                order_id=order_id,
            )

    def _submit_command(
        self,
        command: TradingCommand,
    ) -> PlacedOrder | None:
        if isinstance(command, PlaceBuyLimitCommand):
            return self.order_executor.place_limit_buy(
                account_id=self.account_id,
                instrument_id=command.instrument_id,
                quantity=command.quantity,
                price=command.price,
            )

        if isinstance(command, PlaceSellLimitCommand):
            return self.order_executor.place_limit_sell(
                account_id=self.account_id,
                instrument_id=command.instrument_id,
                quantity=command.quantity,
                price=command.price,
            )

        if isinstance(command, PlaceSellAllLimitCommand):
            return self.order_executor.place_limit_sell(
                account_id=self.account_id,
                instrument_id=command.instrument_id,
                quantity=command.quantity,
                price=command.price,
            )

        return None
