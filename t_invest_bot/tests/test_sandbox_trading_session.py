from decimal import Decimal

from application.sandbox_trading_session import SandboxTradingSession
from broker.live_order_manager import LiveOrderManager
from domain.order_execution import PlacedOrder
from strategy.grid_engine import GridEngine, GridEngineConfig, GridLevel

from broker.order_execution_event_mapper import OrderExecutionEventMapper
from broker.order_state_tracker import OrderStateTracker
from domain.order_state import OrderExecutionState



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


 
class FakeExecutedStateProvider:
    def get_order_state(
        self,
        account_id: str,
        order_id: str,
    ) -> OrderExecutionState:
        return OrderExecutionState(
            order_id=order_id,
            is_executed=True,
            executed_quantity=1,
            executed_price=Decimal("298.10"),
        )


def test_sandbox_trading_session_polls_executions_and_updates_grid() -> None:
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

    tracker = OrderStateTracker(
        account_id="account-1",
        live_order_manager=live_order_manager,
        order_state_provider=FakeExecutedStateProvider(),
    )

    session = SandboxTradingSession(
        grid_engine=grid,
        live_order_manager=live_order_manager,
        order_state_tracker=tracker,
        execution_event_mapper=OrderExecutionEventMapper(),
    )

    session.on_price(Decimal("299"))
    session.on_price(Decimal("298"))
    session.on_price(Decimal("298.10"))

    events = session.poll_executions()

    assert len(events) == 1
    assert events[0].side == "BUY"
    assert len(session.executed_events) == 1
    assert live_order_manager.active_orders == {}

def test_sandbox_trading_session_releases_reserved_capital_after_buy_execution() -> None:
    from application.portfolio_manager import PortfolioManager
    from application.trade_capital_service import TradeCapitalService
    from domain.portfolio import Portfolio
    from portfolio.capital_reservation_manager import CapitalReservationManager

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

    trade_capital_service = TradeCapitalService(
        portfolio_manager=PortfolioManager(
            portfolio=Portfolio(
                cash=Decimal("1000"),
            )
        ),
        reservation_manager=CapitalReservationManager(
            available_cash=Decimal("1000"),
        ),
    )

    live_order_manager = LiveOrderManager(
        account_id="account-1",
        order_executor=executor,
        trade_capital_service=trade_capital_service,
    )

    tracker = OrderStateTracker(
        account_id="account-1",
        live_order_manager=live_order_manager,
        order_state_provider=FakeExecutedStateProvider(),
    )

    session = SandboxTradingSession(
        grid_engine=grid,
        live_order_manager=live_order_manager,
        order_state_tracker=tracker,
        execution_event_mapper=OrderExecutionEventMapper(),
    )

    session.on_price(Decimal("299"))
    session.on_price(Decimal("298"))
    session.on_price(Decimal("298.10"))

    assert trade_capital_service.reservation_manager.get_reserved_total() > Decimal("0")

    session.poll_executions()

    assert trade_capital_service.reservation_manager.get_reserved_total() == Decimal("0")
