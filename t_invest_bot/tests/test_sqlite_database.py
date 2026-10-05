from pathlib import Path
import sqlite3

from head_server.storage import HeadStorage
from infrastructure.sqlite.trading_account_repository import TradingAccountRepository

from infrastructure.sqlite.sqlite_database import SQLiteDatabase


def test_startup_repairs_missing_columns_before_indexes_and_keeps_rows(tmp_path):
    path = tmp_path / "old.db"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE money_movements(id INTEGER PRIMARY KEY, amount TEXT)")
        connection.execute("INSERT INTO money_movements VALUES(1, '123')")
    database = SQLiteDatabase(path)
    database.initialize()
    database.initialize()
    with database.connect() as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(money_movements)")}
        assert {"created_at", "trading_account_id", "note"} <= columns
        assert connection.execute("SELECT amount FROM money_movements WHERE id=1").fetchone()[0] == "123"
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_head_startup_adds_missing_columns_without_deleting_client(tmp_path):
    path = tmp_path / "head.db"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE clients(id INTEGER PRIMARY KEY, login TEXT, api_key TEXT)")
        connection.execute("INSERT INTO clients VALUES(1, 'kept', 'test')")
    HeadStorage(str(path))
    HeadStorage(str(path))
    with sqlite3.connect(path) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(clients)")}
        assert {"machine_label", "password_reset_code_hash", "latest_payload"} <= columns
        assert connection.execute("SELECT login FROM clients WHERE id=1").fetchone()[0] == "kept"
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_account_startup_preserves_legacy_encrypted_token(tmp_path):
    path = tmp_path / "accounts.db"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE trading_accounts(id TEXT PRIMARY KEY, protected_token TEXT)")
        connection.execute("INSERT INTO trading_accounts VALUES('old', 'encrypted-test')")
    TradingAccountRepository(str(path))
    TradingAccountRepository(str(path))
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT protected_credentials FROM trading_accounts").fetchone()[0] == "encrypted-test"


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


def test_sqlite_database_migrates_legacy_columns(
    tmp_path: Path,
) -> None:
    database = SQLiteDatabase(
        database_path=tmp_path / "legacy.db",
    )

    with database.connect() as connection:
        connection.executescript(
            """
            CREATE TABLE operations_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                trading_account_id TEXT,
                instrument_id TEXT,
                ticker TEXT,
                event_type TEXT NOT NULL,
                details TEXT NOT NULL
            );

            CREATE TABLE commission_charges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                broker TEXT NOT NULL,
                instrument_id TEXT,
                ticker TEXT,
                level_index INTEGER,
                trade_profit TEXT NOT NULL,
                percent TEXT NOT NULL,
                amount TEXT NOT NULL,
                balance_after TEXT NOT NULL
            );

            INSERT INTO operations_log (
                created_at,
                event_type,
                details
            )
            VALUES (
                '2026-01-01T00:00:00+00:00',
                'ORDER_RECONCILE',
                'legacy row'
            );
            """
        )

    database.initialize()

    with database.connect() as connection:
        operation_columns = {
            row[1]
            for row in connection.execute(
                """
                PRAGMA table_info(
                    operations_log
                )
                """
            )
        }

        charge_columns = {
            row[1]
            for row in connection.execute(
                """
                PRAGMA table_info(
                    commission_charges
                )
                """
            )
        }

        indexes = {
            row["name"]
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'index'
                """
            )
        }

        legacy_row = connection.execute(
            """
            SELECT head_synced
            FROM operations_log
            WHERE id = 1
            """
        ).fetchone()

    assert "head_synced" in operation_columns
    assert "trading_account_id" in charge_columns
    assert "synced_with_head" in charge_columns
    assert "idx_operations_log_head_synced" in indexes
    assert "idx_commission_charges_account" in indexes
    assert legacy_row["head_synced"] == 0
