import sqlite3
from sqlite_schema import SchemaConnection
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class SQLiteDatabase:
    database_path: Path

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, factory=SchemaConnection)
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

                CREATE TABLE IF NOT EXISTS reconciliation_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    trading_account_id TEXT,
                    instrument_id TEXT,
                    event_type TEXT NOT NULL,
                    details TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS operations_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    trading_account_id TEXT,
                    instrument_id TEXT,
                    ticker TEXT,
                    event_type TEXT NOT NULL,
                    details TEXT NOT NULL,
                    head_synced INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS money_movements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    trading_account_id TEXT NOT NULL,
                    amount TEXT NOT NULL,
                    note TEXT NOT NULL DEFAULT ''
                );

                CREATE INDEX IF NOT EXISTS idx_money_movements_account
                ON money_movements (
                    trading_account_id
                );

                CREATE TABLE IF NOT EXISTS balance_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    trading_account_id TEXT NOT NULL,
                    currency TEXT NOT NULL,
                    equity TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_balance_snapshots_account
                ON balance_snapshots (
                    trading_account_id
                );

                CREATE TABLE IF NOT EXISTS account_backfills (
                    trading_account_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS broker_cash_flows (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trading_account_id TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    currency TEXT NOT NULL,
                    payment TEXT NOT NULL
                );

                CREATE UNIQUE INDEX IF NOT EXISTS idx_broker_cash_flows_dedup
                ON broker_cash_flows (
                    trading_account_id,
                    occurred_at,
                    kind,
                    payment
                );

                CREATE INDEX IF NOT EXISTS idx_broker_cash_flows_account
                ON broker_cash_flows (
                    trading_account_id
                );

                CREATE TABLE IF NOT EXISTS broker_operations (
                    trading_account_id TEXT NOT NULL,
                    operation_id TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    currency TEXT NOT NULL,
                    payment TEXT NOT NULL,
                    instrument_id TEXT,
                    ticker TEXT,
                    quantity TEXT,
                    PRIMARY KEY (trading_account_id, operation_id)
                );

                CREATE INDEX IF NOT EXISTS idx_broker_operations_date
                ON broker_operations (occurred_at);

                CREATE TABLE IF NOT EXISTS broker_operation_sync (
                    trading_account_id TEXT PRIMARY KEY,
                    covered_since TEXT NOT NULL,
                    synced_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS instrument_statistics (
                    instrument_id TEXT PRIMARY KEY,
                    total_cycles INTEGER NOT NULL,
                    profitable_cycles INTEGER NOT NULL,
                    losing_cycles INTEGER NOT NULL,
                    total_profit TEXT NOT NULL,
                    max_drawdown TEXT NOT NULL,
                    average_cycle_profit TEXT NOT NULL,
                    compensation_closes INTEGER NOT NULL,
                    total_trades INTEGER NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS commission_charges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    trading_account_id TEXT,
                    broker TEXT NOT NULL,
                    instrument_id TEXT,
                    ticker TEXT,
                    level_index INTEGER,
                    trade_profit TEXT NOT NULL,
                    percent TEXT NOT NULL,
                    amount TEXT NOT NULL,
                    balance_after TEXT NOT NULL,
                    synced_with_head INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS cabinet_entitlements (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    payload_json TEXT NOT NULL,
                    local_charge_id INTEGER NOT NULL,
                    balance TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS commission_settings_cache (
                    broker TEXT PRIMARY KEY,
                    percent TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )

            existing_columns = {
                row[1]
                for row in connection.execute(
                    """
                    PRAGMA table_info(
                        operations_log
                    )
                    """
                ).fetchall()
            }

            if (
                "head_synced"
                not in existing_columns
            ):
                connection.execute(
                    """
                    ALTER TABLE operations_log
                    ADD COLUMN head_synced
                        INTEGER NOT NULL
                        DEFAULT 0
                    """
                )

            charge_columns = {
                row[1]
                for row in connection.execute(
                    """
                    PRAGMA table_info(
                        commission_charges
                    )
                    """
                ).fetchall()
            }

            if (
                "trading_account_id"
                not in charge_columns
            ):
                connection.execute(
                    """
                    ALTER TABLE commission_charges
                    ADD COLUMN trading_account_id
                        TEXT
                    """
                )

            if (
                "synced_with_head"
                not in charge_columns
            ):
                connection.execute(
                    """
                    ALTER TABLE commission_charges
                    ADD COLUMN synced_with_head
                        INTEGER NOT NULL
                        DEFAULT 0
                    """
                )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_operations_log_head_synced
                ON operations_log (
                    head_synced
                )
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_commission_charges_account
                ON commission_charges (
                    trading_account_id
                )
                """
            )
