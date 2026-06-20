from dataclasses import dataclass
from datetime import datetime, timezone

from application.api_usage_recorder import (
    ApiUsageEvent,
    ApiUsageSummary,
)
from infrastructure.sqlite.sqlite_database import SQLiteDatabase


@dataclass(slots=True)
class SQLiteApiUsageRepository:
    database: SQLiteDatabase

    def save_event(
        self,
        event: ApiUsageEvent,
    ) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO api_usage_events (
                    created_at,
                    source,
                    operation,
                    weight,
                    session_id,
                    ticker
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    event.created_at.isoformat(),
                    event.source,
                    event.operation,
                    event.weight,
                    event.session_id,
                    event.ticker,
                ),
            )

    def record(
        self,
        source: str,
        operation: str,
        weight: int = 1,
        session_id: str | None = None,
        ticker: str | None = None,
    ) -> None:
        self.save_event(
            ApiUsageEvent(
                created_at=datetime.now(timezone.utc),
                source=source,
                operation=operation,
                weight=weight,
                session_id=session_id,
                ticker=ticker,
            )
        )

    def summarize(self) -> ApiUsageSummary:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT operation, SUM(weight) AS total_weight, COUNT(*) AS events_count
                FROM api_usage_events
                GROUP BY operation
                """
            ).fetchall()

        by_operation: dict[str, int] = {}
        total_weight = 0
        events_count = 0

        for row in rows:
            operation_weight = int(row["total_weight"])
            by_operation[row["operation"]] = operation_weight
            total_weight += operation_weight
            events_count += int(row["events_count"])

        return ApiUsageSummary(
            total_weight=total_weight,
            events_count=events_count,
            by_operation=by_operation,
        )
