from decimal import Decimal

from application.portfolio_manager import (
    PortfolioManager,
)
from application.sandbox_trading_session import (
    SandboxTradingSession,
)
from application.trade_capital_service import (
    TradeCapitalService,
)
from broker.live_order_manager import (
    LiveOrderManager,
)
from broker.order_execution_event_mapper import (
    OrderExecutionEventMapper,
)
from broker.order_state_tracker import (
    OrderStateTracker,
)
from domain.order_execution import (
    PlacedOrder,
)
from domain.order_state import (
    OrderExecutionState,
)
from domain.portfolio import (
    Portfolio,
)
from portfolio.capital_reservation_manager import (
    CapitalReservationManager,
)
from strategy.grid_engine import (
    GridEngine,
    GridEngineConfig,
    GridLevel,
)


class FakeOrderExecutor:
    def __init__(
        self,
    ) -> None:
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

        self.placed_orders.append(
            order
        )

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

        self.placed_orders.append(
            order
        )

        return order

    def cancel_order(
        self,
        account_id: str,
        order_id: str,
    ) -> None:
        self.canceled_orders.append(
            (
                account_id,
                order_id,
            )
        )


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

            executed_price=Decimal(
                "298.70"
            ),

            executed_commission=(
                Decimal("0.30")
            ),

            total_order_amount=(
                Decimal("298.70")
            ),

            status="FILLED",
        )


def create_grid(
) -> GridEngine:
    return GridEngine(
        instrument_id="SBER",

        levels=[
            GridLevel(
                index=1,
                price=Decimal(
                    "299"
                ),
            )
        ],

        config=GridEngineConfig(
            quantity=1,

            #
            # Первый trailing:
            # ±0.50% от start price.
            #
            first_entry_activation_percent=(
                Decimal("0.50")
            ),

            #
            # BUY trailing:
            # 0.15% под максимумом.
            #
            entry_rebound_percent=(
                Decimal("0.15")
            ),

            #
            # BUY limit:
            # 0.15% выше рынка.
            #
            entry_limit_offset_percent=(
                Decimal("0.15")
            ),
        ),

        #
        # Цена запуска сессии.
        #
        session_start_price=(
            Decimal("300")
        ),

        #
        # Для теста достаточно
        # фиксированного шага 1 ₽.
        #
        grid_step=(
            Decimal("1")
        ),
    )


def move_session_to_buy_order(
    session: SandboxTradingSession,
) -> list[PlacedOrder]:
    #
    # Старт = 300.
    #
    # 0.5% вниз:
    #
    # 300 × 0.995 = 298.50
    #
    # Здесь BUY trailing
    # активируется.
    #
    assert (
        session.on_price(
            Decimal("298.50")
        )
        == []
    )

    level = (
        session
        .grid_engine
        .levels[0]
    )

    assert (
        level.trailing_entry
        is not None
    )

    #
    # Цена пошла вверх.
    #
    # Trailing должен немедленно
    # подтянуться за новым максимумом.
    #
    assert (
        session.on_price(
            Decimal("299.00")
        )
        == []
    )

    trailing_state = (
        level.trailing_entry
    )

    assert (
        trailing_state
        is not None
    )

    assert (
        trailing_state.highest_price
        == Decimal("299.00")
    )

    trigger_price = (
        trailing_state
        .trigger_price
    )

    assert (
        trigger_price
        is not None
    )

    #
    # Цена откатывается вниз
    # и касается trailing.
    #
    # Теперь должен появиться
    # лимитный BUY выше рынка.
    #
    return session.on_price(
        trigger_price
    )


def test_sandbox_trading_session_places_order_from_grid_signal(
) -> None:
    grid = create_grid()

    executor = (
        FakeOrderExecutor()
    )

    live_order_manager = (
        LiveOrderManager(
            account_id="account-1",
            order_executor=executor,
        )
    )

    session = (
        SandboxTradingSession(
            grid_engine=grid,

            live_order_manager=(
                live_order_manager
            ),
        )
    )

    #
    # До 0.50% ничего
    # происходить не должно.
    #
    assert (
        session.on_price(
            Decimal("298.51")
        )
        == []
    )

    assert (
        grid.levels[0]
        .trailing_entry
        is None
    )

    placed_orders = (
        move_session_to_buy_order(
            session=session,
        )
    )

    assert (
        len(placed_orders)
        == 1
    )

    assert (
        len(
            session.placed_orders
        )
        == 1
    )

    assert (
        len(
            executor.placed_orders
        )
        == 1
    )

    assert (
        "buy-1"
        in live_order_manager
        .active_orders
    )


def test_sandbox_trading_session_stop_cancels_orders(
) -> None:
    grid = create_grid()

    executor = (
        FakeOrderExecutor()
    )

    live_order_manager = (
        LiveOrderManager(
            account_id="account-1",
            order_executor=executor,
        )
    )

    session = (
        SandboxTradingSession(
            grid_engine=grid,

            live_order_manager=(
                live_order_manager
            ),
        )
    )

    placed_orders = (
        move_session_to_buy_order(
            session=session,
        )
    )

    assert (
        len(placed_orders)
        == 1
    )

    assert (
        "buy-1"
        in live_order_manager
        .active_orders
    )

    session.stop()

    assert (
        len(
            executor
            .canceled_orders
        )
        == 1
    )

    assert (
        executor
        .canceled_orders[0]
        == (
            "account-1",
            "buy-1",
        )
    )


def test_sandbox_trading_session_polls_executions_and_updates_grid(
) -> None:
    grid = create_grid()

    executor = (
        FakeOrderExecutor()
    )

    live_order_manager = (
        LiveOrderManager(
            account_id="account-1",
            order_executor=executor,
        )
    )

    tracker = (
        OrderStateTracker(
            account_id="account-1",

            live_order_manager=(
                live_order_manager
            ),

            order_state_provider=(
                FakeExecutedStateProvider()
            ),
        )
    )

    session = (
        SandboxTradingSession(
            grid_engine=grid,

            live_order_manager=(
                live_order_manager
            ),

            order_state_tracker=(
                tracker
            ),

            execution_event_mapper=(
                OrderExecutionEventMapper()
            ),
        )
    )

    placed_orders = (
        move_session_to_buy_order(
            session=session,
        )
    )

    assert (
        len(placed_orders)
        == 1
    )

    events = (
        session.poll_executions()
    )

    assert (
        len(events)
        == 1
    )

    assert (
        events[0].side
        == "BUY"
    )

    assert (
        events[0].price
        == Decimal("298.70")
    )

    assert (
        events[0].commission
        == Decimal("0.30")
    )

    assert (
        len(
            session.executed_events
        )
        == 1
    )

    assert (
        live_order_manager
        .active_orders
        == {}
    )

    #
    # BUY должен создать
    # отдельную позицию уровня.
    #
    assert (
        1
        in grid.open_positions
    )

    position = (
        grid.open_positions[1]
    )

    assert (
        position.entry_price
        == Decimal("298.70")
    )


def test_sandbox_trading_session_releases_reserved_capital_after_buy_execution(
) -> None:
    grid = create_grid()

    executor = (
        FakeOrderExecutor()
    )

    trade_capital_service = (
        TradeCapitalService(
            portfolio_manager=(
                PortfolioManager(
                    portfolio=(
                        Portfolio(
                            cash=Decimal(
                                "1000"
                            ),
                        )
                    )
                )
            ),

            reservation_manager=(
                CapitalReservationManager(
                    available_cash=(
                        Decimal("1000")
                    ),
                )
            ),
        )
    )

    live_order_manager = (
        LiveOrderManager(
            account_id="account-1",

            order_executor=(
                executor
            ),

            trade_capital_service=(
                trade_capital_service
            ),
        )
    )

    tracker = (
        OrderStateTracker(
            account_id="account-1",

            live_order_manager=(
                live_order_manager
            ),

            order_state_provider=(
                FakeExecutedStateProvider()
            ),
        )
    )

    session = (
        SandboxTradingSession(
            grid_engine=grid,

            live_order_manager=(
                live_order_manager
            ),

            order_state_tracker=(
                tracker
            ),

            execution_event_mapper=(
                OrderExecutionEventMapper()
            ),
        )
    )

    placed_orders = (
        move_session_to_buy_order(
            session=session,
        )
    )

    assert (
        len(placed_orders)
        == 1
    )

    #
    # Пока BUY находится
    # у брокера, капитал
    # зарезервирован.
    #
    assert (
        trade_capital_service
        .reservation_manager
        .get_reserved_total()
        > Decimal("0")
    )

    session.poll_executions()

    #
    # После исполнения BUY
    # резерв снимается.
    #
    assert (
        trade_capital_service
        .reservation_manager
        .get_reserved_total()
        == Decimal("0")
    )


def test_buy_limit_is_above_current_market_after_trailing_touch(
) -> None:
    grid = create_grid()

    executor = (
        FakeOrderExecutor()
    )

    live_order_manager = (
        LiveOrderManager(
            account_id="account-1",
            order_executor=executor,
        )
    )

    session = (
        SandboxTradingSession(
            grid_engine=grid,

            live_order_manager=(
                live_order_manager
            ),
        )
    )

    session.on_price(
        Decimal("298.50")
    )

    session.on_price(
        Decimal("299.00")
    )

    state = (
        grid
        .levels[0]
        .trailing_entry
    )

    assert state is not None

    current_market_price = (
        state.trigger_price
    )

    assert (
        current_market_price
        is not None
    )

    placed_orders = (
        session.on_price(
            current_market_price
        )
    )

    assert (
        len(placed_orders)
        == 1
    )

    #
    # Сам PlacedOrder хранит
    # broker IDs, а цену команды
    # можно проверить через
    # active_orders.
    #
    record = (
        live_order_manager
        .active_orders[
            "buy-1"
        ]
    )

    assert (
        record.command.price
        > current_market_price
    )

    assert (
        record.command.price
        == (
            current_market_price
            * Decimal("1.0015")
        )
    )
