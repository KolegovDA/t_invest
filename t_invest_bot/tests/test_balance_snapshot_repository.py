from datetime import (
    datetime,
    timedelta,
    timezone,
)
from decimal import Decimal
from pathlib import Path

from domain.balance_snapshot import (
    BalanceSnapshot,
)
from infrastructure.sqlite.balance_snapshot_repository import (
    SQLiteBalanceSnapshotRepository,
)
from infrastructure.sqlite.sqlite_database import (
    SQLiteDatabase,
)


now = datetime.now(
    timezone.utc,
)


def make_repository(
    tmp_path: Path,
) -> (
    SQLiteBalanceSnapshotRepository
):
    database = (
        SQLiteDatabase(
            database_path=(
                tmp_path
                / "test.db"
            ),
        )
    )

    database\
        .initialize()

    return (
        SQLiteBalanceSnapshotRepository(
            database=(
                database
            ),
        )
    )


def snapshot(
    created_at: datetime,
    equity: str,
    currency: str = "RUB",
    trading_account_id: str = "account-1",
) -> BalanceSnapshot:
    return (
        BalanceSnapshot(
            created_at=(
                created_at
                .isoformat()
            ),

            trading_account_id=(
                trading_account_id
            ),

            currency=(
                currency
            ),

            equity=Decimal(
                equity
            ),
        )
    )


def test_record_if_due_limits_snapshots_to_fifteen_seconds(tmp_path):
    repository = make_repository(tmp_path)
    repository.record_if_due(snapshot(now, "100"))
    repository.record_if_due(snapshot(now + timedelta(seconds=5), "101"))
    repository.record_if_due(snapshot(now + timedelta(seconds=16), "102"))
    repository.record_if_due(snapshot(now + timedelta(seconds=5), "200", trading_account_id="account-2"))
    recorded = repository.get_since((now - timedelta(seconds=1)).isoformat())
    assert len(recorded) == 3
    assert [item.equity for item in recorded] == [Decimal("100"), Decimal("102"), Decimal("200")]


def test_record_and_get_since(
    tmp_path,
):
    repository = (
        make_repository(
            tmp_path,
        )
    )

    repository\
        .record(
            snapshot=(
                snapshot(
                    now
                    - timedelta(
                        days=1,
                    ),

                    "100.5",
                )
            ),
        )

    repository\
        .record(
            snapshot=(
                snapshot(
                    now,

                    "110",

                    currency=(
                        "USDT"
                    ),

                    trading_account_id=(
                        "account-2"
                    ),
                )
            ),
        )

    snapshots = (
        repository
        .get_since(
            since=(
                (
                    now
                    - timedelta(
                        days=2,
                    )
                )
                .isoformat()
            ),
        )
    )

    assert (
        len(
            snapshots
        )
        == 2
    )

    assert (
        snapshots[
            0
        ]
        .equity
        == Decimal(
            "100.5"
        )
    )

    assert (
        snapshots[
            0
        ]
        .currency
        == "RUB"
    )

    assert (
        snapshots[
            1
        ]
        .currency
        == "USDT"
    )

    assert (
        snapshots[
            1
        ]
        .trading_account_id
        == "account-2"
    )

    assert (
        snapshots[
            1
        ]
        .id
        is not None
    )

    recent = (
        repository
        .get_since(
            since=(
                now
                .isoformat()
            ),
        )
    )

    assert (
        len(
            recent
        )
        == 1
    )


def test_delete_older_than(
    tmp_path,
):
    repository = (
        make_repository(
            tmp_path,
        )
    )

    repository\
        .record(
            snapshot=(
                snapshot(
                    now
                    - timedelta(
                        days=200,
                    ),

                    "100",
                )
            ),
        )

    repository\
        .record(
            snapshot=(
                snapshot(
                    now,

                    "110",
                )
            ),
        )

    repository\
        .delete_older_than(
            cutoff=(
                (
                    now
                    - timedelta(
                        days=180,
                    )
                )
                .isoformat()
            ),
        )

    remaining = (
        repository
        .get_since(
            since=(
                "2000-01-01T00:00:00+00:00"
            ),
        )
    )

    assert (
        len(
            remaining
        )
        == 1
    )

    assert (
        remaining[
            0
        ]
        .equity
        == Decimal(
            "110"
        )
    )
