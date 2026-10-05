from dataclasses import dataclass

from domain.operation_event import (
    OperationEvent,
)
from infrastructure.sqlite.sqlite_database import (
    SQLiteDatabase,
)


CONTROL_EVENT_TYPES = (
    "ORDER_RECONCILE",
    "POSITION_CLEARED",
    "POSITION_MISMATCH",
    "RECONCILE_ERROR",
)


@dataclass(slots=True)
class OperationLogEntry:
    """
    Запись журнала
    операций с локальным
    id — для отправки
    контрольных логов
    на головной сервер.
    """

    id: int
    created_at: str
    event_type: str
    trading_account_id: (
        str | None
    )
    instrument_id: (
        str | None
    )
    ticker: (
        str | None
    )
    details: str

    def to_dict(
        self,
    ) -> dict:
        return {
            "source_id": (
                self.id
            ),

            "created_at": (
                self
                .created_at
            ),

            "trading_account_id": (
                self
                .trading_account_id
            ),

            "instrument_id": (
                self
                .instrument_id
            ),

            "ticker": (
                self.ticker
            ),

            "event_type": (
                self
                .event_type
            ),

            "details": (
                self.details
            ),
        }


def _row_to_entry(
    row,
) -> OperationLogEntry:
    return OperationLogEntry(
        id=int(
            row["id"]
        ),

        created_at=str(
            row[
                "created_at"
            ]
        ),

        event_type=str(
            row[
                "event_type"
            ]
        ),

        trading_account_id=(
            row[
                "trading_account_id"
            ]
        ),

        instrument_id=(
            row[
                "instrument_id"
            ]
        ),

        ticker=(
            row[
                "ticker"
            ]
        ),

        details=str(
            row[
                "details"
            ]
        ),
    )


@dataclass(slots=True)
class SQLiteOperationLogRepository:
    database: SQLiteDatabase

    def record(
        self,
        event: OperationEvent,
    ) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO operations_log (
                    created_at,
                    trading_account_id,
                    instrument_id,
                    ticker,
                    event_type,
                    details
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    event.created_at,
                    event.trading_account_id,
                    event.instrument_id,
                    event.ticker,
                    event.event_type,
                    event.details,
                ),
            )

    def get_since(
        self,
        since: str,
        event_types: (
            list[str]
            | None
        ) = None,
    ) -> (
        list[OperationEvent]
    ):
        query = (
            """
            SELECT
                created_at,
                trading_account_id,
                instrument_id,
                ticker,
                event_type,
                details
            FROM operations_log
            WHERE created_at >= ?
            """
        )

        params: list = [
            since,
        ]

        if event_types:
            placeholders = (
                ", ".join(
                    "?"
                    for _ in (
                        event_types
                    )
                )
            )

            query += (
                f" AND event_type IN ({placeholders})"
            )

            params.extend(
                event_types
            )

        query += (
            """
            ORDER BY id ASC
            """
        )

        with self.database.connect() as connection:
            rows = connection.execute(
                query,
                params,
            ).fetchall()

        return [
            OperationEvent(
                created_at=(
                    row[
                        "created_at"
                    ]
                ),

                event_type=(
                    row[
                        "event_type"
                    ]
                ),

                trading_account_id=(
                    row[
                        "trading_account_id"
                    ]
                ),

                instrument_id=(
                    row[
                        "instrument_id"
                    ]
                ),

                ticker=(
                    row[
                        "ticker"
                    ]
                ),

                details=(
                    row[
                        "details"
                    ]
                ),
            )

            for row in rows
        ]

    def pending_control_logs(
        self,
        limit: int = 200,
    ) -> (
        list[
            OperationLogEntry
        ]
    ):
        """
        Контрольные события
        сверки, ещё не
        отправленные на
        головной сервер.
        """

        placeholders = (
            ", ".join(
                "?"
                for _ in (
                    CONTROL_EVENT_TYPES
                )
            )
        )

        with self.database.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT
                    id,
                    created_at,
                    trading_account_id,
                    instrument_id,
                    ticker,
                    event_type,
                    details
                FROM operations_log
                WHERE head_synced = 0
                    AND event_type IN (
                        {placeholders}
                    )
                ORDER BY id ASC
                LIMIT ?
                """,
                (
                    *CONTROL_EVENT_TYPES,
                    limit,
                ),
            ).fetchall()

        return [
            _row_to_entry(
                row
            )

            for row in rows
        ]

    def mark_control_logs_synced(
        self,
        entry_ids: (
            list[int]
        ),
    ) -> None:
        if not entry_ids:
            return

        placeholders = (
            ", ".join(
                "?"
                for _ in (
                    entry_ids
                )
            )
        )

        with self.database.connect() as connection:
            connection.execute(
                f"""
                UPDATE operations_log
                SET head_synced = 1
                WHERE id IN (
                    {placeholders}
                )
                """,
                tuple(
                    entry_ids
                ),
            )

    def recent(
        self,
        limit: int = 100,
    ) -> (
        list[OperationEvent]
    ):
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    created_at,
                    trading_account_id,
                    instrument_id,
                    ticker,
                    event_type,
                    details
                FROM operations_log
                ORDER BY id DESC
                LIMIT ?
                """,
                (
                    limit,
                ),
            ).fetchall()

        return [
            OperationEvent(
                created_at=(
                    row[
                        "created_at"
                    ]
                ),

                trading_account_id=(
                    row[
                        "trading_account_id"
                    ]
                ),

                instrument_id=(
                    row[
                        "instrument_id"
                    ]
                ),

                ticker=(
                    row[
                        "ticker"
                    ]
                ),

                event_type=(
                    row[
                        "event_type"
                    ]
                ),

                details=(
                    row[
                        "details"
                    ]
                ),
            )

            for row in rows
        ]
