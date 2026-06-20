from pathlib import Path

from infrastructure.sqlite.sqlite_database import SQLiteDatabase
from infrastructure.sqlite.web_session_repository import (
    SQLiteWebSessionRepository,
)
from web.session_registry import WebSession


def test_sqlite_web_session_repository_saves_and_loads_sessions(
    tmp_path: Path,
) -> None:
    database = SQLiteDatabase(
        database_path=tmp_path / "test.db",
    )
    database.initialize()

    repository = SQLiteWebSessionRepository(
        database=database,
    )

    repository.save_session(
        WebSession(
            ticker="SBER",
            levels=20,
            quantity=1,
            status="ACTIVE",
            positions=2,
            current_price=317,
            realized_profit=10,
            unrealized_profit=5,
        )
    )

    sessions = repository.load_sessions()

    assert len(sessions) == 1

    session = sessions[0]

    assert session.ticker == "SBER"
    assert session.levels == 20
    assert session.quantity == 1
    assert session.status == "ACTIVE"
    assert session.positions == 2
    assert session.current_price == 317
    assert session.total_profit == 15
