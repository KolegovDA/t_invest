from dataclasses import dataclass

from domain.operation_event import (
    OperationEvent,
)
from infrastructure.sqlite.sqlite_database import (
    SQLiteDatabase,
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
