from decimal import Decimal

from application.live_order_manager_state_mapper import (
    LiveOrderManagerStateMapper,
)
from broker.live_order_manager import (
    LiveOrderManager,
    LiveOrderRecord,
)
from domain.commands import (
    PlaceBuyLimitCommand,
    PlaceSellLimitCommand,
)
from domain.order_execution import (
    PlacedOrder,
)


class FakeOrderExecutor:
    def place_limit_buy(
        self,
        **kwargs,
    ):
        raise AssertionError(
            "Broker order must NOT "
            "be placed during recovery"
        )

    def place_limit_sell(
        self,
        **kwargs,
    ):
        raise AssertionError(
            "Broker order must NOT "
            "be placed during recovery"
        )

    def cancel_order(
        self,
        **kwargs,
    ):
        pass


def test_active_sell_order_survives_restart() -> None:
    original = LiveOrderManager(
        account_id="LIVE",
        order_executor=(
            FakeOrderExecutor()
        ),
    )

    command = (
        PlaceSellLimitCommand(
            instrument_id="SBER_UID",
            level_index=3,
            quantity=1,
            price=Decimal(
                "300.15"
            ),
        )
    )

    original.active_orders[
        "broker-order-123"
    ] = LiveOrderRecord(
        command=command,
        placed_order=(
            PlacedOrder(
                order_id=(
                    "broker-order-123"
                ),
                request_id=(
                    "request-123"
                ),
            )
        ),
    )

    mapper = (
        LiveOrderManagerStateMapper()
    )

    states = mapper.to_states(
        ticker="SBER",
        manager=original,
    )

    assert len(states) == 1

    assert (
        states[0]
        .broker_order_id
        == "broker-order-123"
    )

    assert (
        states[0].side
        == "SELL"
    )

    assert (
        states[0].level_index
        == 3
    )

    #
    # Полный рестарт:
    # создаём новый manager.
    #
    restored = LiveOrderManager(
        account_id="LIVE",
        order_executor=(
            FakeOrderExecutor()
        ),
    )

    assert (
        restored.active_orders
        == {}
    )

    mapper.restore(
        manager=restored,
        states=states,
    )

    assert (
        "broker-order-123"
        in restored.active_orders
    )

    record = (
        restored.active_orders[
            "broker-order-123"
        ]
    )

    assert isinstance(
        record.command,
        PlaceSellLimitCommand,
    )

    assert (
        record.command
        .instrument_id
        == "SBER_UID"
    )

    assert (
        record.command
        .level_index
        == 3
    )

    assert (
        record.command.quantity
        == 1
    )

    assert (
        record.command.price
        == Decimal("300.15")
    )

    assert (
        record
        .placed_order
        .order_id
        == "broker-order-123"
    )


def test_active_buy_order_survives_restart() -> None:
    original = LiveOrderManager(
        account_id="LIVE",
        order_executor=(
            FakeOrderExecutor()
        ),
    )

    command = (
        PlaceBuyLimitCommand(
            instrument_id="GAZP_UID",
            level_index=7,
            quantity=2,
            price=Decimal(
                "124.50"
            ),
        )
    )

    original.active_orders[
        "buy-order"
    ] = LiveOrderRecord(
        command=command,
        placed_order=(
            PlacedOrder(
                order_id="buy-order",
                request_id=(
                    "buy-request"
                ),
            )
        ),
    )

    mapper = (
        LiveOrderManagerStateMapper()
    )

    states = mapper.to_states(
        ticker="GAZP",
        manager=original,
    )

    restored = LiveOrderManager(
        account_id="LIVE",
        order_executor=(
            FakeOrderExecutor()
        ),
    )

    mapper.restore(
        manager=restored,
        states=states,
    )

    record = (
        restored.active_orders[
            "buy-order"
        ]
    )

    assert isinstance(
        record.command,
        PlaceBuyLimitCommand,
    )

    assert (
        record.command
        .level_index
        == 7
    )

    assert (
        record.command.quantity
        == 2
    )
