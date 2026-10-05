from decimal import Decimal

from broker.broker_order_reconciler import (
    OrderReconcileResult,
)

from application.broker_position_reconciler import (
    PositionReconcileReport,
)
from application.reconciliation_journal import (
    ReconciliationJournal,
)


class FakeRepository:
    def __init__(
        self,
    ):
        self.events = []

    def record(
        self,
        event,
    ):
        self.events.append(
            event
        )


class FakeOperationLog:
    def __init__(
        self,
    ):
        self.records = []

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
        self.records.append(
            {
                "event_type": (
                    event_type
                ),

                "trading_account_id": (
                    trading_account_id
                ),

                "instrument_id": (
                    instrument_id
                ),

                "details": (
                    details
                ),
            }
        )


class BrokenRepository:
    def record(
        self,
        event,
    ):
        raise RuntimeError(
            "database is locked"
        )


class BrokenOperationLog:
    def record(
        self,
        **kwargs,
    ):
        raise RuntimeError(
            "operation log is locked"
        )


def test_journal_skips_results_without_changes() -> None:
    repository = FakeRepository()

    journal = ReconciliationJournal(
        repository=repository,
    )

    journal.record_order_result(
        trading_account_id="tinvest:123",
        result=OrderReconcileResult(
            instrument_id="SBER_UID",
        ),
    )

    assert repository.events == []


def test_journal_records_order_reconcile_result() -> None:
    repository = FakeRepository()

    journal = ReconciliationJournal(
        repository=repository,
    )

    result = (
        OrderReconcileResult(
            instrument_id="SBER_UID",
        )
    )

    result.adopted_orders = 1

    result.reverted_entry_levels = 2

    journal.record_order_result(
        trading_account_id="tinvest:123",
        result=result,
    )

    assert len(repository.events) == 1

    event = repository.events[0]

    assert (
        event.event_type
        == "ORDER_RECONCILE"
    )

    assert (
        event.trading_account_id
        == "tinvest:123"
    )

    assert (
        event.instrument_id
        == "SBER_UID"
    )

    assert (
        "adopted=1"
        in event.details
    )

    assert (
        "reverted_entry=2"
        in event.details
    )


def test_journal_records_position_report() -> None:
    repository = FakeRepository()

    journal = ReconciliationJournal(
        repository=repository,
    )

    report = (
        PositionReconcileReport()
    )

    report.instruments_cleared.append(
        "SBER_UID"
    )

    report.mismatch_warnings.append(
        "BROKER POSITION MISMATCH: SBER_UID"
    )

    journal.record_position_report(
        trading_account_id="tinvest:123",
        report=report,
    )

    assert len(repository.events) == 2

    types = [
        event.event_type
        for event
        in repository.events
    ]

    assert (
        "POSITION_CLEARED"
        in types
    )

    assert (
        "POSITION_MISMATCH"
        in types
    )


def test_journal_records_error() -> None:
    repository = FakeRepository()

    journal = ReconciliationJournal(
        repository=repository,
    )

    journal.record_error(
        trading_account_id=None,
        stage="orders",
        error=TimeoutError(
            "timeout"
        ),
    )

    assert len(repository.events) == 1

    event = repository.events[0]

    assert (
        event.event_type
        == "RECONCILE_ERROR"
    )

    assert (
        "stage=orders"
        in event.details
    )


def test_journal_never_raises_on_repository_failure() -> None:
    journal = ReconciliationJournal(
        repository=BrokenRepository(),
    )

    result = (
        OrderReconcileResult(
            instrument_id="SBER_UID",
        )
    )

    result.adopted_orders = 1

    #
    # Ошибка журнала не должна
    # ломать торговый тик.
    #
    journal.record_order_result(
        trading_account_id="tinvest:123",
        result=result,
    )


def test_journal_without_repository_is_noop() -> None:
    journal = ReconciliationJournal()

    result = (
        OrderReconcileResult(
            instrument_id="SBER_UID",
        )
    )

    result.unknown_broker_orders = 3

    journal.record_order_result(
        trading_account_id=None,
        result=result,
    )


def test_journal_duplicates_events_to_operation_log() -> None:
    repository = FakeRepository()

    operation_log = (
        FakeOperationLog()
    )

    journal = ReconciliationJournal(
        repository=repository,

        operation_log=(
            operation_log
        ),
    )

    journal.record_error(
        trading_account_id=(
            "tinvest:123"
        ),

        stage="positions",

        error=TimeoutError(
            "timeout"
        ),
    )

    assert len(
        repository.events
    ) == 1

    assert len(
        operation_log.records
    ) == 1

    record = (
        operation_log
        .records[0]
    )

    assert (
        record[
            "event_type"
        ]
        == "RECONCILE_ERROR"
    )

    assert (
        record[
            "trading_account_id"
        ]
        == "tinvest:123"
    )

    assert (
        "stage=positions"
        in record[
            "details"
        ]
    )


def test_journal_without_repository_writes_operation_log() -> None:
    operation_log = (
        FakeOperationLog()
    )

    journal = ReconciliationJournal(
        operation_log=(
            operation_log
        ),
    )

    journal.record_error(
        trading_account_id=None,
        stage="orders",

        error=TimeoutError(
            "timeout"
        ),
    )

    assert len(
        operation_log.records
    ) == 1


def test_journal_position_cleared_details_include_cost() -> None:
    repository = FakeRepository()

    journal = ReconciliationJournal(
        repository=repository,
    )

    report = (
        PositionReconcileReport()
    )

    report.instruments_cleared.append(
        "SBER_UID"
    )

    report\
        .cleared_purchase_cost[
            "SBER_UID"
        ] = Decimal(
            "596.00"
        )

    journal.record_position_report(
        trading_account_id=(
            "tinvest:123"
        ),

        report=report,
    )

    event = (
        repository
        .events[0]
    )

    assert (
        "стоимость=596.00"
        in event.details
    )


def test_journal_never_raises_on_operation_log_failure() -> None:
    repository = FakeRepository()

    journal = ReconciliationJournal(
        repository=repository,

        operation_log=(
            BrokenOperationLog()
        ),
    )

    journal.record_error(
        trading_account_id=None,
        stage="orders",

        error=TimeoutError(
            "timeout"
        ),
    )

    assert len(
        repository.events
    ) == 1
