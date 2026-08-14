from decimal import Decimal
from types import SimpleNamespace

from application.trading_session_state_service import (
    TradingSessionStateService,
)
from broker.live_order_manager import (
    LiveOrderManager,
    LiveOrderRecord,
)
from domain.commands import (
    PlaceSellLimitCommand,
)
from domain.events import (
    TradeExecutedEvent,
)
from domain.order_execution import (
    PlacedOrder,
)
from domain.portfolio import (
    Portfolio,
)
from infrastructure.sqlite.trading_state_repository import (
    TradingStateRepository,
)
from portfolio.capital_reservation_manager import (
    CapitalReservationManager,
)
from application.portfolio_manager import (
    PortfolioManager,
)
from application.trade_capital_service import (
    TradeCapitalService,
)
from strategy.grid_engine import (
    GridEngine,
    GridEngineConfig,
    GridLevel,
)


class FakeOrderExecutor:
    def place_limit_buy(
        self,
        **kwargs,
    ):
        raise AssertionError(
            "No broker call expected"
        )

    def place_limit_sell(
        self,
        **kwargs,
    ):
        raise AssertionError(
            "No broker call expected"
        )

    def cancel_order(
        self,
        **kwargs,
    ):
        pass


def create_context():
    engine = GridEngine(
        instrument_id="SBER_UID",
        levels=[
            GridLevel(
                index=1,
                price=Decimal("300"),
            ),
            GridLevel(
                index=2,
                price=Decimal("290"),
            ),
        ],
        config=GridEngineConfig(
            quantity=1,
        ),
    )

    manager = LiveOrderManager(
        account_id="BROKER_ACCOUNT",
        order_executor=(
            FakeOrderExecutor()
        ),
    )

    trading_session = (
        SimpleNamespace(
            grid_engine=engine,
            live_order_manager=manager,
        )
    )

    portfolio_manager = (
        PortfolioManager(
            portfolio=Portfolio(
                cash=Decimal("10000"),
            )
        )
    )

    reservation_manager = (
        CapitalReservationManager(
            available_cash=Decimal(
                "10000"
            )
        )
    )

    trade_capital_service = (
        TradeCapitalService(
            portfolio_manager=(
                portfolio_manager
            ),
            reservation_manager=(
                reservation_manager
            ),
        )
    )

    context = SimpleNamespace(
        account_id="BROKER_ACCOUNT",
        mode="live",

        session=SimpleNamespace(
            sessions={
                "SBER_UID":
                    trading_session
            }
        ),

        portfolio_manager=(
            portfolio_manager
        ),

        trade_capital_service=(
            trade_capital_service
        ),

        tickers_by_instrument_id={
            "SBER_UID":
                "SBER"
        },
    )

    return (
        context,
        engine,
        manager,
        reservation_manager,
    )


def test_full_session_state_survives_restart(
    tmp_path,
) -> None:
    repository = (
        TradingStateRepository(
            db_path=str(
                tmp_path
                / "test.db"
            )
        )
    )

    service = (
        TradingSessionStateService(
            repository=repository,
        )
    )

    (
        context,
        engine,
        manager,
        reservation_manager,
    ) = create_context()

    #
    # BUY уже исполнен.
    #
    engine.on_trade_executed(
        TradeExecutedEvent(
            instrument_id="SBER_UID",
            level_index=1,
            side="BUY",
            quantity=1,
            price=Decimal("300"),
        )
    )

    #
    # Идёт trailing SELL.
    #
    position = (
        engine.open_positions[1]
    )

    activation_price = (
        engine
        ._calculate_exit_activation_price(
            position
            .hard_take_profit_price
        )
    )

    engine.on_price(
        activation_price
    )

    higher_price = (
        activation_price
        * Decimal("1.01")
    )

    engine.on_price(
        higher_price
    )

    assert (
        position.trailing_exit
        is not None
    )

    saved_highest = (
        position
        .trailing_exit
        .highest_price
    )

    #
    # Уже существует broker SELL.
    #
    sell_command = (
        PlaceSellLimitCommand(
            instrument_id="SBER_UID",
            level_index=1,
            quantity=1,
            price=Decimal("305"),
        )
    )

    manager.active_orders[
        "broker-order-1"
    ] = LiveOrderRecord(
        command=sell_command,
        placed_order=(
            PlacedOrder(
                order_id=(
                    "broker-order-1"
                ),
                request_id=(
                    "request-1"
                ),
            )
        ),
    )

    #
    # Есть зарезервированный BUY
    # по другому уровню.
    #
    reservation_result = (
        reservation_manager.reserve(
            instrument_id="SBER_UID",
            level_index=2,
            amount=Decimal("500"),
        )
    )

    assert (
        reservation_result.success
        is True
    )

    assert (
        reservation_manager
        .available_cash
        == Decimal("9500")
    )

    #
    # Сохраняем snapshot.
    #
    saved = service.save(
        context=context,
        session_id="session-1",
        trading_account_id=(
            "local-account-1"
        ),
    )

    assert (
        saved.reserved_cash
        == Decimal("500")
    )

    assert (
        len(saved.reservations)
        == 1
    )

    #
    # Полный restart:
    # создаём совершенно новый context.
    #
    (
        restored_context,
        restored_engine,
        restored_manager,
        restored_reservation_manager,
    ) = create_context()

    assert (
        restored_engine
        .open_positions
        == {}
    )

    assert (
        restored_manager
        .active_orders
        == {}
    )

    assert (
        restored_reservation_manager
        .reservations
        == {}
    )

    restored = service.restore(
        context=restored_context,
        session_id="session-1",
    )

    assert restored is not None

    #
    # Позиция восстановилась.
    #
    assert (
        len(
            restored_engine
            .open_positions
        )
        == 1
    )

    restored_position = (
        restored_engine
        .open_positions[1]
    )

    assert (
        restored_position.entry_price
        == Decimal("300")
    )

    #
    # SELL trailing продолжился
    # с прежнего максимума.
    #
    assert (
        restored_position
        .trailing_exit
        is not None
    )

    assert (
        restored_position
        .trailing_exit
        .highest_price
        == saved_highest
    )

    #
    # Broker order восстановился.
    #
    assert (
        "broker-order-1"
        in restored_manager
        .active_orders
    )

    restored_order = (
        restored_manager
        .active_orders[
            "broker-order-1"
        ]
    )

    assert (
        restored_order
        .command
        .level_index
        == 1
    )

    #
    # Резерв капитала восстановился.
    #
    assert (
        restored_reservation_manager
        .available_cash
        == Decimal("9500")
    )

    assert (
        (
            "SBER_UID",
            2,
        )
        in restored_reservation_manager
        .reservations
    )

    assert (
        restored_reservation_manager
        .reservations[
            (
                "SBER_UID",
                2,
            )
        ]
        .amount
        == Decimal("500")
    )


def test_snapshot_can_be_updated_many_times(
    tmp_path,
) -> None:
    repository = (
        TradingStateRepository(
            db_path=str(
                tmp_path
                / "test.db"
            )
        )
    )

    service = (
        TradingSessionStateService(
            repository=repository,
        )
    )

    (
        context,
        engine,
        manager,
        reservation_manager,
    ) = create_context()

    service.save(
        context=context,
        session_id="session",
        trading_account_id="a1",
    )

    engine.realized_profit = (
        Decimal("10")
    )

    service.save(
        context=context,
        session_id="session",
        trading_account_id="a1",
    )

    engine.realized_profit = (
        Decimal("25")
    )

    service.save(
        context=context,
        session_id="session",
        trading_account_id="a1",
    )

    restored = repository.get(
        "session"
    )

    assert restored is not None

    assert (
        restored
        .instruments[0]
        .realized_profit
        == Decimal("25")
    )
