from __future__ import annotations

from pathlib import Path

from application.head_server_client import (
    HeadReplicationWorker,
)

from domain.operation_event import (
    OperationEvent,
)

from infrastructure.sqlite.operation_log_repository import (
    SQLiteOperationLogRepository,
)
from infrastructure.sqlite.sqlite_database import (
    SQLiteDatabase,
)
from infrastructure.sqlite.user_repository import (
    SQLiteUserRepository,
)


def test_replication_reports_bound_port_without_claiming_external_reachability(monkeypatch):
    from application.head_server_client import HeadServerClient

    monkeypatch.delenv("ESM_WEB_BIND_HOST", raising=False)
    monkeypatch.delenv("ESM_WEB_BOUND_PORT", raising=False)
    assert HeadServerClient.software_endpoint() is None
    monkeypatch.setenv("ESM_WEB_BIND_HOST", "0.0.0.0")
    monkeypatch.setenv("ESM_WEB_BOUND_PORT", "8003")
    monkeypatch.setattr("application.head_server_client.socket.gethostname", lambda: "client-pc")
    assert HeadServerClient.software_endpoint() == "http://client-pc:8003"
    monkeypatch.setenv("ESM_WEB_BIND_HOST", "::1")
    assert HeadServerClient.software_endpoint() == "http://[::1]:8003"
    monkeypatch.setenv("ESM_WEB_BOUND_PORT", "70000")
    assert HeadServerClient.software_endpoint() is None


def test_commission_charge_retries_and_debits_cabinet_once(tmp_path):
    from decimal import Decimal
    from application.commission_service import CommissionService
    from application.portfolio_manager import PortfolioManager
    from application.trade_event_handler import TradeEventHandler
    from domain.events import TradeExecutedEvent
    from domain.portfolio import Portfolio
    from infrastructure.sqlite.commission_repository import SQLiteCommissionRepository
    from head_server.storage import HeadStorage

    database = SQLiteDatabase(tmp_path / "client.db")
    database.initialize()
    repository = SQLiteCommissionRepository(database)
    commission = CommissionService(repository)
    handler = TradeEventHandler(
        portfolio_manager=PortfolioManager(Portfolio(cash=Decimal("1000"))),
        commission_service=commission, broker="tinvest", trading_account_id="account-1",
    )
    handler.handle(TradeExecutedEvent("asset", 1, "BUY", 1, Decimal("100"), Decimal("0")))
    handler.handle(TradeExecutedEvent("asset", 1, "SELL", 1, Decimal("110"), Decimal("0")))
    assert repository.get_balance() == Decimal("-3.00")
    storage = HeadStorage(str(tmp_path / "head.db"))
    attempts = []

    class RetryClient:
        def push_sync(self, api_key, payload):
            for charge in payload.get("commission_charges", []):
                storage.record_commission_charge(1, charge, "test-device")
            attempts.append(payload)
            return len(attempts) > 1

    worker = HeadReplicationWorker(
        client=RetryClient(), payload_builder=FakePayloadBuilder(),
        user_repository=make_user_repository(tmp_path), commission_repository=repository,
    )
    assert not worker.sync_now()
    assert len(repository.pending_unsynced()) == 1
    assert worker.sync_now()
    assert repository.pending_unsynced() == []
    assert storage.get_commission_balance(1) == Decimal("-3.00")
    assert len(storage.list_commission_charges(1)) == 1


class FakePayloadBuilder:
    def build(
        self,
    ) -> dict:
        return {
            "accounts": [],
        }


class FakePushClient:
    def __init__(
        self,
        success: bool,
    ) -> None:
        self.success = (
            success
        )

        self.payloads = []

    def push_sync(
        self,
        api_key: str,
        payload: dict,
    ) -> bool:
        self.payloads.append(
            payload
        )

        return (
            self
            .success
        )


def make_user_repository(
    tmp_path: Path,
) -> (
    SQLiteUserRepository
):
    repository = (
        SQLiteUserRepository(
            db_path=str(
                tmp_path
                / "auth.db"
            ),
        )
    )

    repository.create_user(
        full_name=(
            "Тест Тестов"
        ),
        phone="+79990000000",
        email="test@example.com",
        birth_date="1990-01-01",
        login="tester",
        password_hash=(
            "salt$digest"
        ),
    )

    repository\
        .set_user_head_api_key(
            user_id=1,
            api_key=(
                "head-key-1"
            ),
        )

    return repository


def make_operation_repository(
    tmp_path: Path,
) -> (
    SQLiteOperationLogRepository
):
    database = (
        SQLiteDatabase(
            database_path=(
                tmp_path
                / "operations.db"
            ),
        )
    )

    database.initialize()

    return (
        SQLiteOperationLogRepository(
            database=(
                database
            ),
        )
    )


def record_event(
    repository: (
        SQLiteOperationLogRepository
    ),

    event_type: str,
) -> None:
    repository.record(
        OperationEvent(
            created_at=(
                "2026-09-30T00:00:00+00:00"
            ),
            event_type=(
                event_type
            ),
            trading_account_id=(
                "2011718042"
            ),
            instrument_id=(
                "ALRS_UID"
            ),
            ticker="ALRS",
            details=(
                "позиции закрыты вне бота, уровни освобождены"
            ),
        )
    )


def test_sync_sends_only_control_events_and_marks_synced(
    tmp_path: Path,
) -> None:
    operations = (
        make_operation_repository(
            tmp_path
        )
    )

    record_event(
        operations,
        "ORDER_PLACED",
    )

    record_event(
        operations,
        "POSITION_CLEARED",
    )

    record_event(
        operations,
        "RECONCILE_ERROR",
    )

    client = (
        FakePushClient(
            success=True,
        )
    )

    worker = (
        HeadReplicationWorker(
            client=(
                client
            ),
            payload_builder=(
                FakePayloadBuilder()
            ),
            user_repository=(
                make_user_repository(
                    tmp_path
                )
            ),
            operation_log_repository=(
                operations
            ),
        )
    )

    assert (
        worker
        .sync_now()
        is True
    )

    assert (
        len(
            client
            .payloads
        )
        == 1
    )

    control_logs = (
        client
        .payloads[
            0
        ]
        [
            "control_logs"
        ]
    )

    assert [
        entry[
            "event_type"
        ]

        for entry
        in control_logs
    ] == [
        "POSITION_CLEARED",
        "RECONCILE_ERROR",
    ]

    assert (
        control_logs[
            0
        ]
        [
            "source_id"
        ]
        == 2
    )

    assert (
        operations
        .pending_control_logs()
        == []
    )


def test_failed_sync_keeps_control_logs_pending(
    tmp_path: Path,
) -> None:
    operations = (
        make_operation_repository(
            tmp_path
        )
    )

    record_event(
        operations,
        "POSITION_MISMATCH",
    )

    client = (
        FakePushClient(
            success=False,
        )
    )

    worker = (
        HeadReplicationWorker(
            client=(
                client
            ),
            payload_builder=(
                FakePayloadBuilder()
            ),
            user_repository=(
                make_user_repository(
                    tmp_path
                )
            ),
            operation_log_repository=(
                operations
            ),
        )
    )

    assert (
        worker
        .sync_now()
        is False
    )

    pending = (
        operations
        .pending_control_logs()
    )

    assert (
        len(
            pending
        )
        == 1
    )

    assert (
        pending[
            0
        ]
        .event_type
        == (
            "POSITION_MISMATCH"
        )
    )

    client.success = (
        True
    )

    assert (
        worker
        .sync_now()
        is True
    )

    assert (
        operations
        .pending_control_logs()
        == []
    )
