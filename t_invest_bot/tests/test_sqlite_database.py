from pathlib import Path

from infrastructure.sqlite.sqlite_database import SQLiteDatabase


def test_sqlite_database_creates_tables(
    tmp_path: Path,
) -> None:
    database = SQLiteDatabase(
        database_path=tmp_path / "test.db",
    )

    database.initialize()

    with database.connect() as connection:
        tables = {
            row["name"]
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """
            )
        }

    assert "sessions" in tables
    assert "levels" in tables
    assert "positions" in tables
    assert "portfolio" in tables
    assert "reservations" in tables
