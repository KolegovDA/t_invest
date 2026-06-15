from dataclasses import dataclass, field
from typing import Protocol

from broker.live_order_manager import LiveOrderManager, LiveOrderRecord
from domain.order_state import OrderExecutionState


class OrderStateProvider(Protocol):
    def get_order_state(
        self,
        account_id: str,
        order_id: str,
    ) -> OrderExecutionState:
        pass


@dataclass(slots=True)
class ExecutedOrder:
    order_record: LiveOrderRecord
    execution_state: OrderExecutionState


@dataclass(slots=True)
class OrderStateTracker:
    account_id: str
    live_order_manager: LiveOrderManager
    order_state_provider: OrderStateProvider
    executed_orders: list[ExecutedOrder] = field(default_factory=list)

    def poll(self) -> list[ExecutedOrder]:
        executed_now: list[ExecutedOrder] = []

        for order_id, order_record in list(
            self.live_order_manager.active_orders.items()
        ):
            state = self.order_state_provider.get_order_state(
                account_id=self.account_id,
                order_id=order_id,
            )

            if not state.is_executed:
                continue

            executed_order = ExecutedOrder(
                order_record=order_record,
                execution_state=state,
            )

            executed_now.append(executed_order)
            self.executed_orders.append(executed_order)

            self.live_order_manager.active_orders.pop(
                order_id,
                None,
            )

        return executed_now
