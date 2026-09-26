from pathlib import Path

from domain.reconciliation_event import (
    ReconciliationEvent,
)
from infrastructure.sqlite.reconciliation_event_repository import (
    SQLiteReconciliationEventRepository,
)
from infrastructure.sqlite.sqlite_database import SQLiteDatabase


def test_reconciliation_event_repository_records_and_returns_recent(
    tmp_path: Path,
) -> None:
    database = SQLiteDatabase(
        database_path=tmp_path / "test.db",
    )

    database.initialize()

    repository = (
        SQLiteReconciliationEventRepository(
            database=database,
        )
    )

    repository.record(
        ReconciliationEvent(
            created_at="2026-09-26T10:00:00+00:00",
            trading_account_id="tinvest:123",
            instrument_id="BBG0013HGTT4",
            event_type="ORDER_RECONCILE",
            details="adopted=1 reverted_entry=0",
        )
    )

    repository.record(
        ReconciliationEvent(
            created_at="2026-09-26T11:00:00+00:00",
            trading_account_id="tinvest:123",
            instrument_id=None,
            event_type="RECONCILE_ERROR",
            details="stage=orders error=TimeoutError()",
        )
    )

    events = repository.recent(
        limit=10,
    )

    assert len(events) == 2

    #
    # Свежие события первыми.
    #
    assert (
        events[0].event_type
        == "RECONCILE_ERROR"
    )

    assert (
        events[1].event_type
        == "ORDER_RECONCILE"
    )

    assert (
        events[1].instrument_id
        == "BBG0013HGTT4"
    )

    assert (
        events[1].details
        == "adopted=1 reverted_entry=0"
    )


def test_reconciliation_event_repository_counts_by_type(
    tmp_path: Path,
) -> None:
    database = SQLiteDatabase(
        database_path=tmp_path / "test.db",
    )

    database.initialize()

    repository = (
        SQLiteReconciliationEventRepository(
            database=database,
        )
    )

    for _ in range(3):
        repository.record(
            ReconciliationEvent(
                created_at="2026-09-26T10:00:00+00:00",
                event_type="POSITION_CLEARED",
                details="позиции закрыты вне бота",
            )
        )

    repository.record(
        ReconciliationEvent(
            created_at="2026-09-26T10:00:00+00:00",
            event_type="POSITION_MISMATCH",
            details="BROKER POSITION MISMATCH",
        )
    )

    counts = repository.count_by_type()

    assert (
        counts["POSITION_CLEARED"]
        == 3
    )

    assert (
        counts["POSITION_MISMATCH"]
        == 1
    )
