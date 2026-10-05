from pathlib import Path

from infrastructure.sqlite.account_backfill_repository import (
    SQLiteAccountBackfillRepository,
)
from infrastructure.sqlite.sqlite_database import (
    SQLiteDatabase,
)


def make_repository(
    tmp_path: Path,
) -> (
    SQLiteAccountBackfillRepository
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
        SQLiteAccountBackfillRepository(
            database=(
                database
            ),
        )
    )


def test_is_done_initially_false(
    tmp_path,
):
    repository = (
        make_repository(
            tmp_path,
        )
    )

    assert (
        repository
        .is_done(
            "account-1",
        )

        is False
    )


def test_mark_done(
    tmp_path,
):
    repository = (
        make_repository(
            tmp_path,
        )
    )

    repository\
        .mark_done(
            trading_account_id=(
                "account-1"
            ),

            created_at=(
                "2026-09-30T00:00:00+00:00"
            ),
        )

    assert (
        repository
        .is_done(
            "account-1",
        )

        is True
    )

    assert (
        repository
        .is_done(
            "account-2",
        )

        is False
    )


def test_mark_done_idempotent(
    tmp_path,
):
    repository = (
        make_repository(
            tmp_path,
        )
    )

    repository\
        .mark_done(
            trading_account_id=(
                "account-1"
            ),

            created_at=(
                "2026-09-29T00:00:00+00:00"
            ),
        )

    repository\
        .mark_done(
            trading_account_id=(
                "account-1"
            ),

            created_at=(
                "2026-09-30T00:00:00+00:00"
            ),
        )

    assert (
        repository
        .is_done(
            "account-1",
        )

        is True
    )
