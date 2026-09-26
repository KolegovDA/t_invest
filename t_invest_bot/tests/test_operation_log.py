from pathlib import Path

from application.operation_log_service import (
    OperationLogService,
)
from application.portfolio_manager import PortfolioManager
from application.trade_event_handler import TradeEventHandler
from decimal import Decimal
from domain.events import TradeExecutedEvent
from domain.operation_event import (
    OperationEvent,
)
from domain.portfolio import Portfolio
from infrastructure.sqlite.operation_log_repository import (
    SQLiteOperationLogRepository,
)
from infrastructure.sqlite.sqlite_database import SQLiteDatabase


def _build_service(
    tmp_path: Path,
) -> tuple[
    SQLiteDatabase,
    SQLiteOperationLogRepository,
    OperationLogService,
]:
    database = SQLiteDatabase(
        database_path=(
            tmp_path / "test.db"
        ),
    )

    database.initialize()

    repository = (
        SQLiteOperationLogRepository(
            database=database,
        )
    )

    service = (
        OperationLogService(
            repository=(
                repository
            ),
        )
    )

    return (
        database,
        repository,
        service,
    )


def test_operation_log_repository_records_and_returns_recent(
    tmp_path: Path,
) -> None:
    (
        _,
        repository,
        _,
    ) = _build_service(
        tmp_path,
    )

    repository.record(
        OperationEvent(
            created_at="2026-09-26T10:00:00+00:00",
            trading_account_id="tinvest:123",
            instrument_id="BBG0013HGTT4",
            ticker="SBER",
            event_type="BUY",
            details="уровень=1 кол-во=10",
        )
    )

    repository.record(
        OperationEvent(
            created_at="2026-09-26T11:00:00+00:00",
            event_type="ACCOUNT_ADDED",
            details="name=Основной",
        )
    )

    events = repository.recent(
        limit=10,
    )

    assert len(events) == 2

    #
    # Свежие операции первыми.
    #
    assert (
        events[0].event_type
        == "ACCOUNT_ADDED"
    )

    assert (
        events[0].ticker
        is None
    )

    assert (
        events[1].event_type
        == "BUY"
    )

    assert (
        events[1].ticker
        == "SBER"
    )


def test_operation_log_service_formats_trade_details(
    tmp_path: Path,
) -> None:
    (
        _,
        repository,
        service,
    ) = _build_service(
        tmp_path,
    )

    service.record_trade(
        trading_account_id="tinvest:123",
        instrument_id="BBG0013HGTT4",
        ticker="SBER",
        side="BUY",
        level_index=2,
        quantity=10,
        price=Decimal("101.5"),
        commission=Decimal("3.05"),
    )

    service.record_trade(
        trading_account_id="tinvest:123",
        instrument_id="BBG0013HGTT4",
        ticker="SBER",
        side="SELL",
        level_index=2,
        quantity=10,
        price=Decimal("105"),
        commission=Decimal("3.15"),
        profit=Decimal("33.8"),
    )

    service.record_order_placed(
        trading_account_id="tinvest:123",
        instrument_id="BBG0013HGTT4",
        ticker="SBER",
        order=type(
            "FakeOrder",
            (),
            {
                "order_id": "777",
            },
        )(),
    )

    events = repository.recent(
        limit=10,
    )

    assert (
        events[0].event_type
        == "ORDER_PLACED"
    )

    assert (
        "order_id=777"
        in events[0].details
    )

    assert (
        events[1].event_type
        == "SELL"
    )

    assert (
        "прибыль=33.8"
        in events[1].details
    )

    assert (
        events[2].event_type
        == "BUY"
    )

    assert (
        "уровень=2"
        in events[2].details
    )

    assert (
        events[2].created_at
        != ""
    )


def test_operation_log_service_never_raises(
    tmp_path: Path,
) -> None:
    class BrokenRepository:
        def record(
            self,
            event,
        ) -> None:
            raise RuntimeError(
                "database error",
            )

    service = (
        OperationLogService(
            repository=(
                BrokenRepository()
            ),
        )
    )

    #
    # Ошибка журнала не должна
    # ломать торговый тик.
    #
    service.record_trade(
        trading_account_id=None,
        instrument_id="SBER",
        ticker="SBER",
        side="BUY",
        level_index=1,
        quantity=1,
        price=Decimal("100"),
        commission=Decimal("0.3"),
    )

    service.record(
        event_type="ACCOUNT_ADDED",
    )


def test_trade_event_handler_logs_buy_and_sell(
    tmp_path: Path,
) -> None:
    (
        _,
        repository,
        service,
    ) = _build_service(
        tmp_path,
    )

    portfolio_manager = (
        PortfolioManager(
            portfolio=Portfolio(
                cash=Decimal(
                    "100000"
                ),
            ),
        )
    )

    handler = (
        TradeEventHandler(
            portfolio_manager=(
                portfolio_manager
            ),

            operation_log=(
                service
            ),

            ticker="SBER",

            trading_account_id=(
                "tinvest:123"
            ),
        )
    )

    handler.handle(
        TradeExecutedEvent(
            instrument_id="BBG0013HGTT4",
            level_index=1,
            side="BUY",
            quantity=10,
            price=Decimal("300"),
            commission=None,
        )
    )

    handler.handle(
        TradeExecutedEvent(
            instrument_id="BBG0013HGTT4",
            level_index=1,
            side="SELL",
            quantity=10,
            price=Decimal("310"),
            commission=Decimal(
                "9.3"
            ),
        )
    )

    events = repository.recent(
        limit=10,
    )

    assert len(events) == 2

    assert (
        events[0].event_type
        == "SELL"
    )

    assert (
        events[0].ticker
        == "SBER"
    )

    assert (
        events[0].trading_account_id
        == "tinvest:123"
    )

    assert (
        "прибыль="
        in events[0].details
    )

    assert (
        events[1].event_type
        == "BUY"
    )
