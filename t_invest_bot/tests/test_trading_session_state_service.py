from datetime import datetime, timezone
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


def test_session_started_at_survives_snapshot_updates_and_restart(tmp_path):
    repository = TradingStateRepository(str(tmp_path / "state.db"))
    service = TradingSessionStateService(repository)
    context = create_context()[0]
    first = service.build_state(context, "session", "account")
    repository.save(first)
    second = service.build_state(context, "session", "account")
    assert first.started_at
    assert second.started_at == first.started_at
    assert repository.get("session").started_at == first.started_at


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


def test_closed_grid_is_archived_once_without_stopping_session(tmp_path):
    from application.operation_log_service import OperationLogService
    from infrastructure.sqlite.sqlite_database import SQLiteDatabase
    from infrastructure.sqlite.operation_log_repository import SQLiteOperationLogRepository

    database = SQLiteDatabase(tmp_path / "history.db")
    database.initialize()
    repository = TradingStateRepository(str(database.database_path))
    log = OperationLogService(SQLiteOperationLogRepository(database))
    service = TradingSessionStateService(repository, operation_log=log)
    context, engine, manager, _ = create_context()
    service.save(context, "session", "account")
    engine.on_trade_executed(TradeExecutedEvent("SBER_UID", 1, "BUY", 1, Decimal("100")))
    log.record_trade("account", "SBER_UID", "SBER", "BUY", 1, 1, Decimal("100"), Decimal("0"))
    engine.on_trade_executed(TradeExecutedEvent("SBER_UID", 1, "SELL", 1, Decimal("110")))
    log.record_trade("account", "SBER_UID", "SBER", "SELL", 1, 1, Decimal("110"), Decimal("0"))
    engine.completed_cycles[-1]["events_until"] = datetime.now(timezone.utc).isoformat()
    assert engine.completed_cycles
    engine.completed_cycles[0]["price_points"] = [{"time": engine.completed_cycles[0]["started_at"], "price": "100"}, {"time": engine.completed_cycles[0]["closed_at"], "price": "110"}]
    service.save(context, "session", "account")
    assert repository.get("session").status == "RUNNING"
    grids = repository.closed_grids()
    assert len(grids) == 1
    assert grids[0]["ticker"] == "SBER"
    assert grids[0]["closed_orders"] == 1
    assert len(grids[0]["price_points"]) == 2
    assert [event["side"] for event in grids[0]["events"]] == ["BUY", "SELL"]
    service.save(context, "session", "account")
    assert len(repository.closed_grids()) == 1


def test_closed_grid_archive_failure_retries_after_restart_without_duplicates(tmp_path, monkeypatch):
    import pytest

    repository = TradingStateRepository(str(tmp_path / "archive-retry.db"))
    service = TradingSessionStateService(repository)
    context, engine, _, _ = create_context()
    service.save(context, "session", "account")
    engine.on_trade_executed(TradeExecutedEvent("SBER_UID", 1, "BUY", 1, Decimal("100")))
    engine.on_trade_executed(TradeExecutedEvent("SBER_UID", 1, "SELL", 1, Decimal("110")))
    original = TradingStateRepository.record_closed_grid
    monkeypatch.setattr(TradingStateRepository, "record_closed_grid", lambda *args: (_ for _ in ()).throw(RuntimeError("archive unavailable")))
    with pytest.raises(RuntimeError, match="archive unavailable"):
        service.save(context, "session", "account")
    assert engine.completed_cycles
    assert repository.get("session").instruments[0].completed_cycles
    monkeypatch.setattr(TradingStateRepository, "record_closed_grid", original)
    restored_context, restored_engine, _, _ = create_context()
    service.restore(restored_context, "session")
    assert restored_engine.completed_cycles
    service.save(restored_context, "session", "account")
    assert len(repository.closed_grids()) == 1
    assert not restored_engine.completed_cycles
    service.save(restored_context, "session", "account")
    assert len(repository.closed_grids()) == 1


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
