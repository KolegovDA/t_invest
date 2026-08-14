from decimal import Decimal

from broker.live_order_manager import (
    LiveOrderManager,
    LiveOrderRecord,
)
from broker.order_state_tracker import (
    OrderStateTracker,
)
from domain.commands import (
    PlaceBuyLimitCommand,
)
from domain.order_execution import (
    PlacedOrder,
)
from domain.order_state import (
    OrderExecutionState,
)


class FakeOrderExecutor:
    def cancel_order(
        self,
        **kwargs,
    ):
        pass


class FakeStateProvider:
    def __init__(
        self,
        state: OrderExecutionState,
    ):
        self.state = state

    def get_order_state(
        self,
        account_id: str,
        order_id: str,
    ) -> OrderExecutionState:
        return self.state


def create_manager(
) -> LiveOrderManager:
    manager = LiveOrderManager(
        account_id="ACCOUNT",
        order_executor=(
            FakeOrderExecutor()
        ),
    )

    manager.active_orders[
        "order-1"
    ] = LiveOrderRecord(
        command=(
            PlaceBuyLimitCommand(
                instrument_id=(
                    "SBER"
                ),
                level_index=1,
                quantity=1,
                price=Decimal(
                    "300"
                ),
            )
        ),

        placed_order=(
            PlacedOrder(
                order_id="order-1",
                request_id=(
                    "request-1"
                ),
            )
        ),
    )

    return manager


def test_filled_order_is_returned_and_removed(
) -> None:
    manager = create_manager()

    tracker = OrderStateTracker(
        account_id="ACCOUNT",

        live_order_manager=(
            manager
        ),

        order_state_provider=(
            FakeStateProvider(
                OrderExecutionState(
                    order_id="order-1",

                    is_executed=True,

                    executed_quantity=1,

                    executed_price=Decimal(
                        "300"
                    ),

                    status="FILLED",
                )
            )
        ),
    )

    result = tracker.poll()

    assert (
        len(
            result.executed_orders
        )
        == 1
    )

    assert (
        result.terminal_orders
        == []
    )

    assert (
        manager.active_orders
        == {}
    )


def test_new_order_remains_active(
) -> None:
    manager = create_manager()

    tracker = OrderStateTracker(
        account_id="ACCOUNT",

        live_order_manager=manager,

        order_state_provider=(
            FakeStateProvider(
                OrderExecutionState(
                    order_id="order-1",

                    is_executed=False,

                    executed_quantity=0,

                    status="NEW",
                )
            )
        ),
    )

    result = tracker.poll()

    assert (
        result.executed_orders
        == []
    )

    assert (
        result.terminal_orders
        == []
    )

    assert (
        "order-1"
        in manager.active_orders
    )


def test_cancelled_order_is_terminal_and_removed(
) -> None:
    manager = create_manager()

    tracker = OrderStateTracker(
        account_id="ACCOUNT",

        live_order_manager=manager,

        order_state_provider=(
            FakeStateProvider(
                OrderExecutionState(
                    order_id="order-1",

                    is_executed=False,

                    executed_quantity=0,

                    status="CANCELLED",

                    is_cancelled=True,
                )
            )
        ),
    )

    result = tracker.poll()

    assert (
        result.executed_orders
        == []
    )

    assert (
        len(
            result.terminal_orders
        )
        == 1
    )

    assert (
        result
        .terminal_orders[0]
        .execution_state
        .status
        == "CANCELLED"
    )

    assert (
        manager.active_orders
        == {}
    )


def test_rejected_order_is_terminal_and_removed(
) -> None:
    manager = create_manager()

    tracker = OrderStateTracker(
        account_id="ACCOUNT",

        live_order_manager=manager,

        order_state_provider=(
            FakeStateProvider(
                OrderExecutionState(
                    order_id="order-1",

                    is_executed=False,

                    executed_quantity=0,

                    status="REJECTED",

                    is_rejected=True,
                )
            )
        ),
    )

    result = tracker.poll()

    assert (
        len(
            result.terminal_orders
        )
        == 1
    )

    assert (
        manager.active_orders
        == {}
    )


def test_partial_fill_remains_active(
) -> None:
    manager = create_manager()

    tracker = OrderStateTracker(
        account_id="ACCOUNT",

        live_order_manager=manager,

        order_state_provider=(
            FakeStateProvider(
                OrderExecutionState(
                    order_id="order-1",

                    is_executed=False,

                    executed_quantity=1,

                    executed_price=Decimal(
                        "300"
                    ),

                    status=(
                        "PARTIALLY_FILLED"
                    ),
                )
            )
        ),
    )

    result = tracker.poll()

    assert (
        result.executed_orders
        == []
    )

    assert (
        result.terminal_orders
        == []
    )

    assert (
        "order-1"
        in manager.active_orders
    )
