from __future__ import annotations

from dataclasses import dataclass
from datetime import (
    datetime,
    timezone,
)
from typing import Any


@dataclass(slots=True)
class ReconciliationJournal:
    """
    Журнал событий сверки состояния
    с брокером (v1.1 стабилизация).

    Любая ошибка журнала не должна
    влиять на торговый тик:
    все записи оборачиваются
    в try/except.

    Все события дополнительно
    дублируются в operations_log,
    чтобы попадать в историю
    операций на Главной.
    """

    repository: Any = None

    operation_log: Any = None

    def record_order_result(
        self,
        trading_account_id: (
            str | None
        ),
        result: Any,
    ) -> None:
        if not result.has_changes:
            return

        self._record(
            trading_account_id=trading_account_id,

            instrument_id=(
                result.instrument_id
            ),

            event_type=(
                "ORDER_RECONCILE"
            ),

            details=(
                "adopted="
                f"{result.adopted_orders} "

                "reverted_entry="
                f"{result.reverted_entry_levels} "

                "reverted_exit="
                f"{result.reverted_exit_levels} "

                "unknown_broker_orders="
                f"{result.unknown_broker_orders}"
            ),
        )

    def record_position_report(
        self,
        trading_account_id: (
            str | None
        ),
        report: Any,
    ) -> None:
        for instrument_id in (
            report.instruments_cleared
        ):
            details = (
                "позиции закрыты "
                "вне бота, уровни "
                "освобождены"
            )

            cleared_cost = (
                report
                .cleared_purchase_cost
                .get(
                    instrument_id
                )
            )

            if (
                cleared_cost
                is not None
            ):
                details += (
                    " стоимость="
                    f"{cleared_cost}"
                )

            self._record(
                trading_account_id=trading_account_id,

                instrument_id=(
                    instrument_id
                ),

                event_type=(
                    "POSITION_CLEARED"
                ),

                details=details,
            )

        for warning in (
            report.mismatch_warnings
        ):
            self._record(
                trading_account_id=trading_account_id,

                instrument_id=None,

                event_type=(
                    "POSITION_MISMATCH"
                ),

                details=warning,
            )

    def record_error(
        self,
        trading_account_id: (
            str | None
        ),
        stage: str,
        error: Exception,
    ) -> None:
        self._record(
            trading_account_id=trading_account_id,

            instrument_id=None,

            event_type=(
                "RECONCILE_ERROR"
            ),

            details=(
                f"stage={stage} "
                f"error={error!r}"
            ),
        )

    def _record(
        self,
        trading_account_id: (
            str | None
        ),
        instrument_id: (
            str | None
        ),
        event_type: str,
        details: str,
    ) -> None:
        if (
            self.repository
            is None
            and self.operation_log
            is None
        ):
            return

        from domain.reconciliation_event import (
            ReconciliationEvent,
        )

        if (
            self.repository
            is not None
        ):
            try:
                self.repository.record(
                    ReconciliationEvent(
                        created_at=(
                            datetime
                            .now(
                                timezone.utc,
                            )
                            .isoformat()
                        ),

                        trading_account_id=(
                            trading_account_id
                        ),

                        instrument_id=(
                            instrument_id
                        ),

                        event_type=(
                            event_type
                        ),

                        details=details,
                    )
                )

            except Exception as error:
                #
                # Журнал не имеет права
                # ломать торговлю.
                #
                print(
                    "RECONCILIATION JOURNAL "
                    "ERROR:",
                    repr(error),
                )

        if (
            self.operation_log
            is not None
        ):
            try:
                self.operation_log.record(
                    event_type=(
                        event_type
                    ),

                    trading_account_id=(
                        trading_account_id
                    ),

                    instrument_id=(
                        instrument_id
                    ),

                    details=details,
                )

            except Exception as error:
                print(
                    "RECONCILIATION JOURNAL "
                    "OPERATION LOG ERROR:",
                    repr(error),
                )
