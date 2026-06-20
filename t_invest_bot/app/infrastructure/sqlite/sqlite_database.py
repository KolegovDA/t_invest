import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class SQLiteDatabase:
    database_path: Path

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    instrument_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS levels (
                    session_id TEXT NOT NULL,
                    level_index INTEGER NOT NULL,
                    price TEXT NOT NULL,
                    status TEXT NOT NULL,
                    PRIMARY KEY (session_id, level_index),
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                );

                CREATE TABLE IF NOT EXISTS positions (
                    session_id TEXT NOT NULL,
                    level_index INTEGER NOT NULL,
                    quantity INTEGER NOT NULL,
                    entry_price TEXT NOT NULL,
                    buy_commission TEXT NOT NULL,
                    expected_sell_commission_percent TEXT NOT NULL,
                    hard_take_profit_price TEXT NOT NULL,
                    PRIMARY KEY (session_id, level_index),
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                );

                CREATE TABLE IF NOT EXISTS portfolio (
                    instrument_id TEXT PRIMARY KEY,
                    quantity INTEGER NOT NULL,
                    average_price TEXT NOT NULL,
                    realized_profit TEXT NOT NULL,
                    buy_commission_total TEXT NOT NULL,
                    last_price TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS reservations (
                    instrument_id TEXT NOT NULL,
                    level_index INTEGER NOT NULL,
                    amount TEXT NOT NULL,
                    PRIMARY KEY (instrument_id, level_index)
                );

                CREATE TABLE IF NOT EXISTS web_sessions (
                    ticker TEXT PRIMARY KEY,
                    levels INTEGER NOT NULL,
                    quantity INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    positions INTEGER NOT NULL,
                    current_price REAL NOT NULL,
                    realized_profit REAL NOT NULL,
                    unrealized_profit REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS api_usage_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    source TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    weight INTEGER NOT NULL,
                    session_id TEXT,
                    ticker TEXT
                );
                """
            )
