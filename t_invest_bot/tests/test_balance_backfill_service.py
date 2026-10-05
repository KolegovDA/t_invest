from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

from application.balance_backfill_service import BalanceBackfillService
from domain.balance_snapshot import BalanceSnapshot
from domain.broker_operation import BrokerOperation
from infrastructure.sqlite.balance_snapshot_repository import SQLiteBalanceSnapshotRepository
from infrastructure.sqlite.broker_cash_flow_repository import SQLiteBrokerCashFlowRepository
from infrastructure.sqlite.sqlite_database import SQLiteDatabase


def make_service(tmp_path):
    database = SQLiteDatabase(tmp_path / "history.db")
    database.initialize()
    snapshots = SQLiteBalanceSnapshotRepository(database)
    operations = SQLiteBrokerCashFlowRepository(database)
    return BalanceBackfillService(
        snapshot_repository=snapshots,
        broker_cash_flow_repository=operations,
    ), snapshots, operations


def test_backfill_imports_all_operations_without_fabricating_equity(tmp_path):
    service, snapshots, repository = make_service(tmp_path)
    now = datetime.now(timezone.utc)
    operations = [
        BrokerOperation(now - timedelta(days=120), "input", Decimal("50"), "RUB", "deposit"),
        BrokerOperation(now - timedelta(days=30), "buy", Decimal("-10"), "RUB", "buy"),
        BrokerOperation(now - timedelta(days=5), "dividend", Decimal("3"), "USD", "dividend"),
    ]
    calls = []

    def get_operations(**kwargs):
        calls.append(kwargs)
        return operations

    adapter = SimpleNamespace(
        get_portfolio=lambda **kwargs: SimpleNamespace(cash=Decimal("70"), total_value=Decimal("100")),
        get_operations=get_operations,
    )
    account = SimpleNamespace(id="account-1", broker_account_id="broker-1", mode="live")
    assert service.backfill_account(account, adapter, {}, "RUB")
    assert calls[0]["currency"] is None
    assert timedelta(days=180) <= datetime.now(timezone.utc) - calls[0]["since"] < timedelta(days=181)
    imported = repository.operations_since((now - timedelta(days=180)).isoformat())
    assert len(imported) == 3
    assert len(repository.get_since((now - timedelta(days=180)).isoformat())) == 1
    recorded = snapshots.get_since((now - timedelta(days=180)).isoformat())
    assert len(recorded) == 1
    assert recorded[0].equity == Decimal("100")
    assert datetime.fromisoformat(recorded[0].created_at) >= now
    assert service.backfill_account(account, adapter, {}, "RUB")
    assert len(calls) == 2
    assert len(repository.operations_since((now - timedelta(days=180)).isoformat())) == 3
    assert len(repository.get_since((now - timedelta(days=180)).isoformat())) == 1
    recorded = snapshots.get_since((now - timedelta(days=180)).isoformat())
    assert len(recorded) == 2
    assert all(datetime.fromisoformat(snapshot.created_at) >= now for snapshot in recorded)


@pytest.mark.parametrize("history_days", [None, 30, 179, 181])
def test_backfill_checks_actual_history_despite_full_sync_marker(tmp_path, history_days):
    service, snapshots, repository = make_service(tmp_path)
    now = datetime.now(timezone.utc)
    account = SimpleNamespace(id="account-1", broker_account_id="broker-1", mode="live")
    repository.mark_synced(account.id, (now - timedelta(days=181)).isoformat(), now.isoformat())
    snapshots.record(BalanceSnapshot(
        created_at=(now - timedelta(days=200)).isoformat(),
        trading_account_id="other-account",
        currency="RUB",
        equity=Decimal("500"),
    ))
    if history_days is not None:
        snapshots.record(BalanceSnapshot(
            created_at=(now - timedelta(days=history_days)).isoformat(),
            trading_account_id=account.id,
            currency="RUB",
            equity=Decimal("100"),
        ))
    calls = []

    def get_operations(**kwargs):
        calls.append(kwargs)
        return []

    adapter = SimpleNamespace(
        get_portfolio=lambda **kwargs: SimpleNamespace(cash=Decimal("100"), total_value=None),
        get_operations=get_operations,
    )
    should_retry = history_days is None or history_days < 180
    assert service.backfill_account(account, adapter, {}, "RUB") is should_retry
    assert len(calls) == int(should_retry)
    assert len(snapshots.get_since("2000-01-01")) == 1 + int(history_days is not None) + int(should_retry)


def test_backfill_imports_operations_when_old_snapshots_have_no_sync_marker(tmp_path):
    service, snapshots, repository = make_service(tmp_path)
    now = datetime.now(timezone.utc)
    account = SimpleNamespace(id="account-1", broker_account_id="broker-1", mode="live")
    snapshots.record(BalanceSnapshot(
        created_at=(now - timedelta(days=181)).isoformat(),
        trading_account_id=account.id,
        currency="RUB",
        equity=Decimal("100"),
    ))
    operation = BrokerOperation(now, "buy", Decimal("-10"), "RUB", "buy")
    adapter = SimpleNamespace(
        get_portfolio=lambda **kwargs: SimpleNamespace(cash=Decimal("90"), total_value=None),
        get_operations=lambda **kwargs: [operation],
    )
    assert service.backfill_account(account, adapter, {}, "RUB")
    assert len(repository.operations_since((now - timedelta(days=180)).isoformat())) == 1


def test_first_snapshot_by_account_uses_timestamp_not_insertion_order(tmp_path):
    _, snapshots, _ = make_service(tmp_path)
    now = datetime.now(timezone.utc)
    for days, equity in [(1, "110"), (181, "100"), (30, "105")]:
        snapshots.record(BalanceSnapshot(
            created_at=(now - timedelta(days=days)).isoformat(),
            trading_account_id="account-1",
            currency="RUB",
            equity=Decimal(equity),
        ))
    first = snapshots.get_first_by_account("account-1")
    assert first is not None
    assert first.created_at == (now - timedelta(days=181)).isoformat()
    assert first.trading_account_id == "account-1"
    assert first.currency == "RUB"
    assert first.equity == Decimal("100")
    assert first.id is not None
    assert snapshots.get_first_by_account("missing-account") is None


def test_backfill_retries_partial_import_idempotently(tmp_path):
    service, snapshots, repository = make_service(tmp_path)
    now = datetime.now(timezone.utc)
    operation = BrokerOperation(now, "sell", Decimal("10"), "RUB", "sell")
    repository.record_operation("account-1", operation)
    account = SimpleNamespace(id="account-1", broker_account_id="broker-1", mode="live")
    adapter = SimpleNamespace(
        get_portfolio=lambda **kwargs: SimpleNamespace(cash=Decimal("10"), total_value=None),
        get_operations=lambda **kwargs: [operation],
    )
    assert service.backfill_account(account, adapter, {}, "RUB")
    assert len(repository.operations_since((now - timedelta(days=180)).isoformat())) == 1
    assert len(snapshots.get_since((now - timedelta(days=180)).isoformat())) == 1


def test_backfill_error_keeps_sync_marker_unset(tmp_path):
    service, snapshots, repository = make_service(tmp_path)

    def get_operations(**kwargs):
        raise RuntimeError("broker offline")

    adapter = SimpleNamespace(
        get_portfolio=lambda **kwargs: SimpleNamespace(cash=Decimal("10"), total_value=None),
        get_operations=get_operations,
    )
    account = SimpleNamespace(id="account-1", broker_account_id="broker-1", mode="live")
    with pytest.raises(RuntimeError):
        service.backfill_account(account, adapter, {}, "RUB")
    assert repository.sync_state(account.id) is None
    assert snapshots.get_since("2000-01-01") == []
