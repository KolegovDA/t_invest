from decimal import Decimal

from broker.live_order_manager import LiveOrderManager
from domain.commands import (
    PlaceBuyLimitCommand,
    PlaceSellAllLimitCommand,
    PlaceSellLimitCommand,
)
from domain.order_execution import PlacedOrder


class FakeOrderExecutor:
    def __init__(self) -> None:
        self.placed_buy_orders = []
        self.placed_sell_orders = []
        self.canceled_orders = []

    def place_limit_buy(
        self,
        account_id: str,
        instrument_id: str,
        quantity: int,
        price: Decimal,
    ) -> PlacedOrder:
        self.placed_buy_orders.append(
            (account_id, instrument_id, quantity, price)
        )

        return PlacedOrder(
            order_id=f"buy-{len(self.placed_buy_orders)}",
            request_id="request-buy",
        )

    def place_limit_sell(
        self,
        account_id: str,
        instrument_id: str,
        quantity: int,
        price: Decimal,
    ) -> PlacedOrder:
        self.placed_sell_orders.append(
            (account_id, instrument_id, quantity, price)
        )

        return PlacedOrder(
            order_id=f"sell-{len(self.placed_sell_orders)}",
            request_id="request-sell",
        )

    def cancel_order(
        self,
        account_id: str,
        order_id: str,
    ) -> None:
        self.canceled_orders.append(
            (account_id, order_id)
        )


def test_live_order_manager_submits_buy_and_sell_commands() -> None:
    executor = FakeOrderExecutor()

    manager = LiveOrderManager(
        account_id="account-1",
        order_executor=executor,
    )

    placed_orders = manager.submit_commands(
        commands=[
            PlaceBuyLimitCommand(
                instrument_id="SBER",
                level_index=1,
                quantity=1,
                price=Decimal("300"),
            ),
            PlaceSellLimitCommand(
                instrument_id="SBER",
                level_index=1,
                quantity=1,
                price=Decimal("303"),
            ),
        ],
    )

    assert len(placed_orders) == 2
    assert len(executor.placed_buy_orders) == 1
    assert len(executor.placed_sell_orders) == 1
    assert len(manager.active_orders) == 2


def test_live_order_manager_submits_sell_all_as_sell() -> None:
    executor = FakeOrderExecutor()

    manager = LiveOrderManager(
        account_id="account-1",
        order_executor=executor,
    )

    placed_orders = manager.submit_commands(
        commands=[
            PlaceSellAllLimitCommand(
                instrument_id="SBER",
                quantity=5,
                price=Decimal("290"),
            )
        ],
    )

    assert len(placed_orders) == 1
    assert len(executor.placed_sell_orders) == 1
    assert executor.placed_sell_orders[0][2] == 5


def test_live_order_manager_cancels_all_orders() -> None:
    executor = FakeOrderExecutor()

    manager = LiveOrderManager(
        account_id="account-1",
        order_executor=executor,
    )

    manager.submit_commands(
        commands=[
            PlaceBuyLimitCommand(
                instrument_id="SBER",
                level_index=1,
                quantity=1,
                price=Decimal("300"),
            ),
            PlaceBuyLimitCommand(
                instrument_id="SBER",
                level_index=2,
                quantity=1,
                price=Decimal("295"),
            ),
        ],
    )

    manager.cancel_all_orders()

    assert len(manager.active_orders) == 0
    assert len(executor.canceled_orders) == 2
