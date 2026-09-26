from dataclasses import dataclass

from domain.reconciliation_event import (
    ReconciliationEvent,
)
from infrastructure.sqlite.sqlite_database import (
    SQLiteDatabase,
)


@dataclass(slots=True)
class SQLiteReconciliationEventRepository:
    database: SQLiteDatabase

    def record(
        self,
        event: ReconciliationEvent,
    ) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO reconciliation_events (
                    created_at,
                    trading_account_id,
                    instrument_id,
                    event_type,
                    details
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    event.created_at,
                    event.trading_account_id,
                    event.instrument_id,
                    event.event_type,
                    event.details,
                ),
            )

    def recent(
        self,
        limit: int = 100,
    ) -> (
        list[ReconciliationEvent]
    ):
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    created_at,
                    trading_account_id,
                    instrument_id,
                    event_type,
                    details
                FROM reconciliation_events
                ORDER BY id DESC
                LIMIT ?
                """,
                (
                    limit,
                ),
            ).fetchall()

        return [
            ReconciliationEvent(
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

    def count_by_type(
        self,
    ) -> dict[
        str,
        int,
    ]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    event_type,
                    COUNT(*) AS events_count
                FROM reconciliation_events
                GROUP BY event_type
                """
            ).fetchall()

        return {
            row[
                "event_type"
            ]: int(
                row[
                    "events_count"
                ]
            )

            for row in rows
        }
