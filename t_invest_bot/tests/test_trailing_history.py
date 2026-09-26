from decimal import Decimal
from types import SimpleNamespace

from application.trading_session_state_service import (
    TradingSessionStateService,
)
from broker.live_order_manager import (
    LiveOrderManager,
)
from domain.events import (
    TradeExecutedEvent,
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


class StubOperationLog:
    def __init__(
        self,
    ):
        self.events = []

    def record(
        self,
        event_type,
        trading_account_id=(
            None
        ),
        instrument_id=(
            None
        ),
        ticker=None,
        details="",
    ):
        self.events.append(
            {
                "event_type":
                    event_type,

                "trading_account_id":
                    trading_account_id,

                "instrument_id":
                    instrument_id,

                "ticker":
                    ticker,

                "details":
                    details,
            }
        )


def create_context():
    engine = GridEngine(
        instrument_id="SBER_UID",
        levels=[
            GridLevel(
                index=1,
                price=Decimal(
                    "300"
                ),
            ),
        ],
        config=(
            GridEngineConfig(
                quantity=1,
            )
        ),
    )

    manager = (
        LiveOrderManager(
            account_id=(
                "BROKER_ACCOUNT"
            ),

            order_executor=(
                FakeOrderExecutor()
            ),
        )
    )

    trading_session = (
        SimpleNamespace(
            grid_engine=(
                engine
            ),

            live_order_manager=(
                manager
            ),
        )
    )

    portfolio_manager = (
        PortfolioManager(
            portfolio=(
                Portfolio(
                    cash=Decimal(
                        "10000"
                    ),
                )
            )
        )
    )

    reservation_manager = (
        CapitalReservationManager(
            available_cash=(
                Decimal(
                    "10000"
                )
            ),
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

    context = (
        SimpleNamespace(
            account_id=(
                "BROKER_ACCOUNT"
            ),

            mode="live",

            session=(
                SimpleNamespace(
                    sessions={
                        "SBER_UID":
                            trading_session
                    }
                )
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
    )

    return (
        context,
        engine,
    )


def _start_trailing(
    engine,
) -> Decimal:
    engine.on_trade_executed(
        TradeExecutedEvent(
            instrument_id=(
                "SBER_UID"
            ),

            level_index=1,

            side="BUY",

            quantity=1,

            price=Decimal(
                "300"
            ),
        )
    )

    position = (
        engine
        .open_positions[1]
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

    return activation_price


def test_trailing_moves_recorded_to_operation_log(
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

    operation_log = (
        StubOperationLog()
    )

    service = (
        TradingSessionStateService(
            repository=(
                repository
            ),

            operation_log=(
                operation_log
            ),
        )
    )

    (
        context,
        engine,
    ) = create_context()

    activation_price = (
        _start_trailing(
            engine
        )
    )

    #
    # Первый snapshot — база,
    # событий нет.
    #
    service.save(
        context=context,

        session_id=(
            "session-1"
        ),

        trading_account_id=(
            "account-1"
        ),
    )

    assert (
        operation_log
        .events
        == []
    )

    #
    # Новый максимум поднял
    # trailing target —
    # одно событие TRAILING.
    #
    engine.on_price(
        activation_price
        * Decimal(
            "1.02"
        )
    )

    service.save(
        context=context,

        session_id=(
            "session-1"
        ),

        trading_account_id=(
            "account-1"
        ),
    )

    trailing_events = [
        event

        for event
        in (
            operation_log
            .events
        )

        if (
            event
            ["event_type"]
            == "TRAILING"
        )
    ]

    assert (
        len(
            trailing_events
        )
        == 1
    )

    event = (
        trailing_events[0]
    )

    assert (
        event
        ["ticker"]
        == "SBER"
    )

    assert (
        event
        ["instrument_id"]
        == "SBER_UID"
    )

    assert (
        "уровень=1"
        in (
            event
            ["details"]
        )
    )

    assert (
        "цена="
        in (
            event
            ["details"]
        )
    )

    #
    # Цена не обновила максимум —
    # новых событий нет.
    #
    service.save(
        context=context,

        session_id=(
            "session-1"
        ),

        trading_account_id=(
            "account-1"
        ),
    )

    trailing_events = [
        event

        for event
        in (
            operation_log
            .events
        )

        if (
            event
            ["event_type"]
            == "TRAILING"
        )
    ]

    assert (
        len(
            trailing_events
        )
        == 1
    )


def test_trailing_moves_skipped_without_operation_log(
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
            repository=(
                repository
            ),
        )
    )

    (
        context,
        engine,
    ) = create_context()

    activation_price = (
        _start_trailing(
            engine
        )
    )

    service.save(
        context=context,

        session_id=(
            "session-2"
        ),

        trading_account_id=(
            "account-1"
        ),
    )

    engine.on_price(
        activation_price
        * Decimal(
            "1.02"
        )
    )

    state = (
        service.save(
            context=context,

            session_id=(
                "session-2"
            ),

            trading_account_id=(
                "account-1"
            ),
        )
    )

    #
    # Журнал не подключён —
    # сохранение работает как
    # раньше, без событий.
    #
    assert (
        state
        .session_id
        == "session-2"
    )
