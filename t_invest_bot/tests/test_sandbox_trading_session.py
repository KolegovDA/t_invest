from decimal import Decimal

from application.sandbox_trading_session import SandboxTradingSession
from broker.live_order_manager import LiveOrderManager
from domain.order_execution import PlacedOrder
from strategy.grid_engine import GridEngine, GridEngineConfig, GridLevel


class FakeOrderExecutor:
    def __init__(self) -> None:
        self.placed_orders = []
        self.canceled_orders = []

    def place_limit_buy(
        self,
        account_id: str,
        instrument_id: str,
        quantity: int,
        price: Decimal,
    ) -> PlacedOrder:
        order = PlacedOrder(
            order_id="buy-1",
            request_id="request-1",
        )

        self.placed_orders.append(order)

        return order

    def place_limit_sell(
        self,
        account_id: str,
        instrument_id: str,
        quantity: int,
        price: Decimal,
    ) -> PlacedOrder:
        order = PlacedOrder(
            order_id="sell-1",
            request_id="request-1",
        )

        self.placed_orders.append(order)

        return order

    def cancel_order(
        self,
        account_id: str,
        order_id: str,
    ) -> None:
        self.canceled_orders.append(
            (account_id, order_id)
        )


def test_sandbox_trading_session_places_order_from_grid_signal() -> None:
    grid = GridEngine(
        instrument_id="SBER",
        levels=[
            GridLevel(
                index=1,
                price=Decimal("300"),
            )
        ],
        config=GridEngineConfig(
            quantity=1,
            entry_rebound_percent=Decimal("0.01"),
            entry_limit_offset_percent=Decimal("0.01"),
        ),
    )

    executor = FakeOrderExecutor()

    live_order_manager = LiveOrderManager(
        account_id="account-1",
        order_executor=executor,
    )

    session = SandboxTradingSession(
        grid_engine=grid,
        live_order_manager=live_order_manager,
    )

    assert session.on_price(Decimal("299")) == []
    assert session.on_price(Decimal("298")) == []

    placed_orders = session.on_price(
        Decimal("298.10")
    )

    assert len(placed_orders) == 1
    assert len(session.placed_orders) == 1


def test_sandbox_trading_session_stop_cancels_orders() -> None:
    grid = GridEngine(
        instrument_id="SBER",
        levels=[
            GridLevel(
                index=1,
                price=Decimal("300"),
            )
        ],
        config=GridEngineConfig(
            quantity=1,
            entry_rebound_percent=Decimal("0.01"),
            entry_limit_offset_percent=Decimal("0.01"),
        ),
    )

    executor = FakeOrderExecutor()

    live_order_manager = LiveOrderManager(
        account_id="account-1",
        order_executor=executor,
    )

    session = SandboxTradingSession(
        grid_engine=grid,
        live_order_manager=live_order_manager,
    )

    session.on_price(Decimal("299"))
    session.on_price(Decimal("298"))
    session.on_price(Decimal("298.10"))

    session.stop()

    assert len(executor.canceled_orders) == 1
