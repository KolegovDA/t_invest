from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

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

    def summarize(
        self,
        active_sessions_count: int = 0,
    ) -> ApiUsageSummary:
        by_operation = self._summarize_by_operation()
        total_weight = sum(by_operation.values())
        events_count = self._count_events()

        last_1s_weight = self._sum_weight_since(
            since=datetime.now(timezone.utc) - timedelta(seconds=1),
        )
        last_60s_weight = self._sum_weight_since(
            since=datetime.now(timezone.utc) - timedelta(seconds=60),
        )
        last_300s_weight = self._sum_weight_since(
            since=datetime.now(timezone.utc) - timedelta(seconds=300),
        )

        if active_sessions_count > 0:
            per_minute_per_session = (
                last_60s_weight / active_sessions_count
            )
        else:
            per_minute_per_session = 0.0

        return ApiUsageSummary(
            total_weight=total_weight,
            events_count=events_count,
            by_operation=by_operation,
            last_1s_weight=last_1s_weight,
            last_60s_weight=last_60s_weight,
            last_300s_weight=last_300s_weight,
            active_sessions_count=active_sessions_count,
            per_minute_per_session=per_minute_per_session,
            forecast_5_sessions_per_minute=per_minute_per_session * 5,
            forecast_10_sessions_per_minute=per_minute_per_session * 10,
            forecast_20_sessions_per_minute=per_minute_per_session * 20,
        )

    def _summarize_by_operation(self) -> dict[str, int]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    operation,
                    SUM(weight) AS total_weight
                FROM api_usage_events
                GROUP BY operation
                """
            ).fetchall()

        return {
            row["operation"]: int(row["total_weight"])
            for row in rows
        }

    def _count_events(self) -> int:
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS events_count
                FROM api_usage_events
                """
            ).fetchone()

        return int(row["events_count"])

    def _sum_weight_since(
        self,
        since: datetime,
    ) -> int:
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT COALESCE(SUM(weight), 0) AS total_weight
                FROM api_usage_events
                WHERE created_at >= ?
                """,
                (
                    since.isoformat(),
                ),
            ).fetchone()

        return int(row["total_weight"])
