from datetime import datetime, timezone

from domain.broker_operation import BrokerOperation

from decimal import (
    Decimal,
)
from pathlib import Path

from domain.broker_cash_flow import (
    BrokerCashFlow,
)
from infrastructure.sqlite.broker_cash_flow_repository import (
    SQLiteBrokerCashFlowRepository,
)
from infrastructure.sqlite.sqlite_database import (
    SQLiteDatabase,
)


def make_repository(
    tmp_path: Path,
) -> (
    SQLiteBrokerCashFlowRepository
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
        SQLiteBrokerCashFlowRepository(
            database=(
                database
            ),
        )
    )


def flow(
    occurred_at: str,

    payment: str,

    kind: str = "input",

    trading_account_id: str = "account-1",

    currency: str = "RUB",
) -> (
    BrokerCashFlow
):
    return (
        BrokerCashFlow(
            trading_account_id=(
                trading_account_id
            ),

            occurred_at=(
                occurred_at
            ),

            kind=kind,

            currency=currency,

            payment=Decimal(
                payment
            ),
        )
    )


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
            flow=(
                flow(
                    "2026-09-01T10:00:00+00:00",

                    "1000",
                )
            ),
        )

    repository\
        .record(
            flow=(
                flow(
                    "2026-09-20T10:00:00+00:00",

                    "-300",

                    kind=(
                        "output"
                    ),

                    trading_account_id=(
                        "account-2"
                    ),
                )
            ),
        )

    flows = (
        repository
        .get_since(
            since=(
                "2026-09-01T00:00:00+00:00"
            ),
        )
    )

    assert (
        len(
            flows
        )

        == 2
    )

    assert (
        flows[
            0
        ]
        .payment
        == Decimal(
            "1000"
        )
    )

    assert (
        flows[
            1
        ]
        .trading_account_id

        == "account-2"
    )

    recent = (
        repository
        .get_since(
            since=(
                "2026-09-10T00:00:00+00:00"
            ),
        )
    )

    assert (
        len(
            recent
        )

        == 1
    )


def test_record_dedup(
    tmp_path,
):
    repository = (
        make_repository(
            tmp_path,
        )
    )

    repository\
        .record(
            flow=(
                flow(
                    "2026-09-01T10:00:00+00:00",

                    "1000",
                )
            ),
        )

    repository\
        .record(
            flow=(
                flow(
                    "2026-09-01T10:00:00+00:00",

                    "1000",
                )
            ),
        )

    flows = (
        repository
        .get_since(
            since=(
                "2000-01-01T00:00:00+00:00"
            ),
        )
    )

    assert (
        len(
            flows
        )

        == 1
    )


def test_operation_ids_preserve_identical_trades_and_currencies(tmp_path):
    repository = make_repository(tmp_path)
    timestamp = datetime.now(timezone.utc)
    for operation_id, currency in [("one", "RUB"), ("two", "RUB"), ("three", "USD")]:
        operation = BrokerOperation(
            timestamp, "buy", Decimal("-100"), currency,
            operation_id, "instrument-1", "ABC", Decimal("10"),
        )
        repository.record_operation("account-1", operation)
        repository.record_operation("account-1", operation)
    entries = repository.operations_since("2000-01-01")
    assert len(entries) == 3
    assert {item.operation_id for _, item in entries} == {"one", "two", "three"}
    assert entries[0][1].quantity == Decimal("10")
    assert entries[0][1].instrument_id == "instrument-1"


def test_sync_marker_keeps_earliest_covered_date(tmp_path):
    repository = make_repository(tmp_path)
    repository.mark_synced("account-1", "2026-04-01", "2026-09-01")
    repository.mark_synced("account-1", "2026-05-01", "2026-10-01")
    assert repository.sync_state("account-1") == ("2026-04-01", "2026-10-01")


def test_last_occurred_at(
    tmp_path,
):
    repository = (
        make_repository(
            tmp_path,
        )
    )

    assert (
        repository
        .last_occurred_at(
            "account-1",
        )

        is None
    )

    repository\
        .record(
            flow=(
                flow(
                    "2026-09-01T10:00:00+00:00",

                    "1000",
                )
            ),
        )

    repository\
        .record(
            flow=(
                flow(
                    "2026-09-02T10:00:00+00:00",

                    "500",

                    kind=(
                        "output"
                    ),
                )
            ),
        )

    assert (
        repository
        .last_occurred_at(
            "account-1",
        )

        == (
            "2026-09-02T10:00:00+00:00"
        )
    )

    assert (
        repository
        .last_occurred_at(
            "account-2",
        )

        is None
    )
