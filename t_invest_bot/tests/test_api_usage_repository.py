from pathlib import Path

from infrastructure.sqlite.api_usage_repository import (
    SQLiteApiUsageRepository,
)
from infrastructure.sqlite.sqlite_database import SQLiteDatabase


def test_api_usage_repository_records_and_summarizes_events(
    tmp_path: Path,
) -> None:
    database = SQLiteDatabase(
        database_path=tmp_path / "test.db",
    )
    database.initialize()

    repository = SQLiteApiUsageRepository(
        database=database,
    )

    repository.record(
        source="tinvest",
        operation="get_last_price",
        weight=1,
        ticker="SBER",
    )

    repository.record(
        source="tinvest",
        operation="get_last_price",
        weight=1,
        ticker="GAZP",
    )

    repository.record(
        source="tinvest",
        operation="get_candles",
        weight=5,
        ticker="SBER",
    )

    summary = repository.summarize()

    assert summary.total_weight == 7
    assert summary.events_count == 3
    assert summary.by_operation["get_last_price"] == 2
    assert summary.by_operation["get_candles"] == 5
