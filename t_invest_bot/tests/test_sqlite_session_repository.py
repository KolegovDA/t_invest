from datetime import datetime
from decimal import Decimal
from pathlib import Path

from infrastructure.sqlite.session_repository import SQLiteSessionRepository
from infrastructure.sqlite.sqlite_database import SQLiteDatabase
from strategy.grid_engine import GridLevel, GridLevelStatus


def test_sqlite_session_repository_saves_and_loads_levels(
    tmp_path: Path,
) -> None:
    database = SQLiteDatabase(
        database_path=tmp_path / "test.db",
    )
    database.initialize()

    repository = SQLiteSessionRepository(
        database=database,
    )

    repository.save_session(
        session_id="session-1",
        account_id="account-1",
        ticker="SBER",
        instrument_id="SBER_ID",
        status="ACTIVE",
        created_at=datetime(2026, 1, 1, 12, 0, 0),
        levels=[
            GridLevel(
                index=1,
                price=Decimal("300"),
                status=GridLevelStatus.WAITING_PRICE,
            ),
            GridLevel(
                index=2,
                price=Decimal("290"),
                status=GridLevelStatus.ORDER_PLACED,
            ),
        ],
    )

    levels = repository.load_levels(
        session_id="session-1",
    )

    assert len(levels) == 2
    assert levels[0].index == 1
    assert levels[0].price == Decimal("300")
    assert levels[0].status == GridLevelStatus.WAITING_PRICE
    assert levels[1].index == 2
    assert levels[1].price == Decimal("290")
    assert levels[1].status == GridLevelStatus.ORDER_PLACED
