from dataclasses import dataclass
from decimal import Decimal

from broker.live_order_manager import LiveOrderManager
from broker.order_state_tracker import OrderStateTracker
from domain.commands import PlaceBuyLimitCommand
from domain.order_execution import PlacedOrder
from domain.order_state import OrderExecutionState


class FakeOrderExecutor:
    def __init__(self) -> None:
        self.counter = 0

    def place_limit_buy(
        self,
        account_id: str,
        instrument_id: str,
        quantity: int,
        price: Decimal,
    ) -> PlacedOrder:
        self.counter += 1

        return PlacedOrder(
            order_id=f"order-{self.counter}",
            request_id=f"request-{self.counter}",
        )

    def place_limit_sell(
        self,
        account_id: str,
        instrument_id: str,
        quantity: int,
        price: Decimal,
    ) -> PlacedOrder:
        self.counter += 1

        return PlacedOrder(
            order_id=f"order-{self.counter}",
            request_id=f"request-{self.counter}",
        )

    def cancel_order(
        self,
        account_id: str,
        order_id: str,
    ) -> None:
        pass


@dataclass
class FakeOrderStateProvider:
    executed_order_ids: set[str]

    def get_order_state(
        self,
        account_id: str,
        order_id: str,
    ) -> OrderExecutionState:
        is_executed = order_id in self.executed_order_ids

        return OrderExecutionState(
            order_id=order_id,
            is_executed=is_executed,
            executed_quantity=1 if is_executed else 0,
            executed_price=Decimal("300") if is_executed else None,
        )


def test_order_state_tracker_removes_executed_order_from_active_orders() -> None:
    live_order_manager = LiveOrderManager(
        account_id="account-1",
        order_executor=FakeOrderExecutor(),
    )

    placed_orders = live_order_manager.submit_commands(
        commands=[
            PlaceBuyLimitCommand(
                instrument_id="SBER",
                level_index=1,
                quantity=1,
                price=Decimal("300"),
            )
        ],
    )

    provider = FakeOrderStateProvider(
        executed_order_ids={
            placed_orders[0].order_id,
        }
    )

    tracker = OrderStateTracker(
        account_id="account-1",
        live_order_manager=live_order_manager,
        order_state_provider=provider,
    )

    executed = tracker.poll()

    assert len(executed) == 1
    assert len(tracker.executed_orders) == 1
    assert live_order_manager.active_orders == {}


def test_order_state_tracker_keeps_not_executed_order_active() -> None:
    live_order_manager = LiveOrderManager(
        account_id="account-1",
        order_executor=FakeOrderExecutor(),
    )

    live_order_manager.submit_commands(
        commands=[
            PlaceBuyLimitCommand(
                instrument_id="SBER",
                level_index=1,
                quantity=1,
                price=Decimal("300"),
            )
        ],
    )

    provider = FakeOrderStateProvider(
        executed_order_ids=set(),
    )

    tracker = OrderStateTracker(
        account_id="account-1",
        live_order_manager=live_order_manager,
        order_state_provider=provider,
    )

    executed = tracker.poll()

    assert executed == []
    assert len(live_order_manager.active_orders) == 1
