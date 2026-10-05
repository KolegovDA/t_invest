from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
from sqlite_schema import SchemaConnection
from dataclasses import dataclass
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from decimal import (
    Decimal,
)
from pathlib import Path
from typing import Any


DEFAULT_DB_NAME = (
    "head_server.db"
)


def utc_now_iso() -> str:
    return (
        datetime
        .now(
            timezone.utc
        )
        .isoformat()
    )


@dataclass(slots=True)
class HeadClient:
    id: int
    created_at: str
    full_name: str
    phone: str
    email: str
    birth_date: str
    login: str
    password_hash: str
    api_key: str
    machine_label: str
    last_sync_at: (
        str | None
    )
    latest_payload: (
        str | None
    )


@dataclass(slots=True)
class HeadStorage:
    """
    Хранилище головного сервера.

    Регистрационные данные
    пользователей клиентских
    копий + реплицируемые
    метрики (счета, платформы,
    инструменты, балансы,
    прибыль) для восстановления
    и мониторинга.
    """

    db_path: str

    def __post_init__(
        self,
    ) -> None:
        self._ensure_database()

    def _connect(
        self,
    ) -> sqlite3.Connection:
        connection = (
            sqlite3
            .connect(
                self.db_path,
                factory=SchemaConnection,
            )
        )

        connection.row_factory = (
            sqlite3.Row
        )

        return connection

    def _ensure_database(
        self,
    ) -> None:
        path = Path(
            self.db_path
        )

        if (
            path.parent
            != Path(".")
        ):
            path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS
                clients (
                    id INTEGER PRIMARY KEY
                        AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    full_name TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    email TEXT NOT NULL,
                    birth_date TEXT NOT NULL,
                    login TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    api_key TEXT NOT NULL
                        UNIQUE,
                    machine_label TEXT NOT NULL
                        DEFAULT '',
                    last_sync_at TEXT,
                    latest_payload TEXT,
                    password_reset_code_hash TEXT,
                    password_reset_expires_at TEXT
                )
                """
            )

            existing_columns = {
                row[1]

                for row
                in connection
                .execute(
                    """
                    PRAGMA table_info(
                        clients
                    )
                    """
                )
                .fetchall()
            }

            if (
                "password_reset_code_hash"
                not in existing_columns
            ):
                connection.execute(
                    """
                    ALTER TABLE clients
                    ADD COLUMN
                        password_reset_code_hash
                        TEXT
                    """
                )

            if (
                "password_reset_expires_at"
                not in existing_columns
            ):
                connection.execute(
                    """
                    ALTER TABLE clients
                    ADD COLUMN
                        password_reset_expires_at
                        TEXT
                    """
                )

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS
                client_syncs (
                    id INTEGER PRIMARY KEY
                        AUTOINCREMENT,
                    client_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_client_syncs_client
                ON client_syncs (
                    client_id
                )
                """
            )

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS
                devices (
                    id INTEGER PRIMARY KEY
                        AUTOINCREMENT,
                    client_id INTEGER NOT NULL,
                    device_key TEXT NOT NULL
                        UNIQUE,
                    machine_label TEXT NOT NULL
                        DEFAULT '',
                    is_head INTEGER NOT NULL
                        DEFAULT 0,
                    created_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL
                )
                """
            )

            device_columns = {row[1] for row in connection.execute("PRAGMA table_info(devices)")}
            for column in ("source_address", "last_sync_payload", "software_endpoint"):
                if column not in device_columns:
                    connection.execute(f"ALTER TABLE devices ADD COLUMN {column} TEXT")

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_devices_client
                ON devices (
                    client_id
                )
                """
            )

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS
                commission_settings (
                    client_id INTEGER NOT NULL,
                    platform TEXT NOT NULL,
                    percent TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (
                        client_id,
                        platform
                    )
                )
                """
            )

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS asset_trading_settings (
                    platform TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    min_profit_percent TEXT,
                    entry_rebound_percent TEXT,
                    trailing_percent TEXT,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (platform, ticker)
                )
                """
            )

            asset_columns = {row[1] for row in connection.execute("PRAGMA table_info(asset_trading_settings)")}
            if "take_profit_percent" not in asset_columns:
                connection.execute("ALTER TABLE asset_trading_settings ADD COLUMN take_profit_percent TEXT")
            migrate_max_tp = "max_take_profit_percent" not in asset_columns
            if migrate_max_tp:
                connection.execute("ALTER TABLE asset_trading_settings ADD COLUMN max_take_profit_percent TEXT")
            migrate_growth = "order_amount_multiplier" not in asset_columns
            for field in ("order_amount_multiplier", "max_order_amount_multiplier"):
                if field not in asset_columns:
                    connection.execute(f"ALTER TABLE asset_trading_settings ADD COLUMN {field} TEXT")
            for ticker, exit_trailing, take_profit, max_take_profit in (
                ("ETHUSDT", "0.1", "0.8", "5"), ("XRPUSDT", "0.1", "0.78", "5"), ("BTCUSDT", "0.05", "1.65", "3"),
                ("LINKUSDT", "0.05", "0.83", "10"), ("TONUSDT", "0.1", "0.8", "3"), ("DOTUSDT", "0.1", "0.8", "3"),
                ("BNBUSDT", "0.05", "0.83", "5"), ("SOLUSDT", "0.1", "1.1", "5"), ("LTCUSDT", "0.1", "0.8", "5"),
                ("DOGEUSDT", "0.1", "1.6", "5"), ("ARBUSDT", "0.05", "0.65", "5"), ("MNTUSDT", "0.05", "0.65", "5"),
                ("AVAXUSDT", "0.05", "0.65", "5"),
            ):
                connection.execute(
                    "INSERT OR IGNORE INTO asset_trading_settings "
                    "(platform, ticker, min_profit_percent, entry_rebound_percent, trailing_percent, updated_at, take_profit_percent, max_take_profit_percent) "
                    "VALUES ('bybit', ?, '0.125', '0.15', ?, ?, ?, ?)",
                    (ticker, exit_trailing, utc_now_iso(), take_profit, max_take_profit),
                )
                if migrate_growth:
                    connection.execute(
                        "UPDATE asset_trading_settings SET order_amount_multiplier = '1.05', max_order_amount_multiplier = '3' WHERE platform = 'bybit' AND ticker = ?", (ticker,),
                    )
                if migrate_max_tp:
                    connection.execute(
                        "UPDATE asset_trading_settings SET max_take_profit_percent = ? WHERE platform = 'bybit' AND ticker = ?",
                        (max_take_profit, ticker),
                    )

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS client_entitlements (
                    client_id INTEGER PRIMARY KEY,
                    trial_ended_at TEXT,
                    allow_insufficient_balance INTEGER NOT NULL DEFAULT 0
                )
                """
            )

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS
                trading_settings (
                    platform TEXT PRIMARY KEY,
                    min_profit_percent TEXT NOT NULL,
                    entry_rebound_percent TEXT NOT NULL,
                    trailing_percent TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS
                commission_charges (
                    id INTEGER PRIMARY KEY
                        AUTOINCREMENT,
                    client_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    broker TEXT NOT NULL,
                    instrument_id TEXT,
                    ticker TEXT,
                    level_index INTEGER,
                    trade_profit TEXT NOT NULL,
                    percent TEXT NOT NULL,
                    amount TEXT NOT NULL,
                    balance_after TEXT NOT NULL
                )
                """
            )

            charge_columns = {
                row[1] for row in connection.execute("PRAGMA table_info(commission_charges)")
            }
            for column in ("source_key", "device_key", "trading_account_id"):
                if column not in charge_columns:
                    connection.execute(f"ALTER TABLE commission_charges ADD COLUMN {column} TEXT")
            connection.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_commission_charge_source "
                "ON commission_charges(client_id, source_key)"
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_commission_charges_client
                ON commission_charges (
                    client_id
                )
                """
            )

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS
                client_control_logs (
                    id INTEGER PRIMARY KEY
                        AUTOINCREMENT,
                    client_id INTEGER NOT NULL,
                    source_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    trading_account_id TEXT,
                    instrument_id TEXT,
                    ticker TEXT,
                    event_type TEXT NOT NULL,
                    details TEXT NOT NULL,
                    UNIQUE (
                        client_id,
                        source_id
                    )
                )
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_client_control_logs_client
                ON client_control_logs (
                    client_id
                )
                """
            )

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS
                topup_requests (
                    id INTEGER PRIMARY KEY
                        AUTOINCREMENT,
                    client_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    amount TEXT NOT NULL,
                    comment TEXT NOT NULL
                        DEFAULT '',
                    document_name TEXT,
                    document_mime TEXT,
                    document_data TEXT,
                    status TEXT NOT NULL
                        DEFAULT 'pending',
                    reviewed_at TEXT,
                    review_note TEXT,
                    balance_after TEXT
                )
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_topup_requests_client
                ON topup_requests (
                    client_id
                )
                """
            )

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS
                device_daily_activity (
                    day TEXT NOT NULL,
                    device_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (
                        day,
                        device_id
                    )
                )
                """
            )

            connection.execute("""
                CREATE TABLE IF NOT EXISTS browser_devices (
                    client_id INTEGER NOT NULL,
                    installation_key TEXT NOT NULL,
                    device_id TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    PRIMARY KEY (client_id, installation_key, device_id)
                )
            """)
            connection.commit()

    def store_browser_devices(self, client_id: int, installation_key: str, devices: list[dict]) -> None:
        if not installation_key.strip() or len(installation_key) > 256 or len(devices) > 100:
            raise ValueError("Invalid browser device batch")
        now = datetime.now(timezone.utc)
        with self._connect() as connection:
            for device in devices:
                device_id = device.get("device_id")
                timestamp = device.get("last_seen_at")
                if not isinstance(device_id, str) or not device_id.strip() or len(device_id) > 256 or not isinstance(timestamp, str):
                    raise ValueError("Invalid browser device")
                seen = datetime.fromisoformat(timestamp)
                if seen.tzinfo is None:
                    seen = seen.replace(tzinfo=timezone.utc)
                if seen > now + timedelta(minutes=5):
                    raise ValueError("Invalid browser activity time")
                connection.execute(
                    "INSERT INTO browser_devices VALUES (?, ?, ?, ?) "
                    "ON CONFLICT(client_id, installation_key, device_id) DO UPDATE "
                    "SET last_seen_at = MAX(browser_devices.last_seen_at, excluded.last_seen_at)",
                    (client_id, installation_key, device_id, seen.astimezone(timezone.utc).isoformat()),
                )

    def list_browser_devices(self) -> list[dict]:
        with self._connect() as connection:
            return [dict(row) for row in connection.execute("SELECT * FROM browser_devices")]

    # ----------------------------------------
    # Clients
    # ----------------------------------------

    def register_client(
        self,
        full_name: str,
        phone: str,
        email: str,
        birth_date: str,
        login: str,
        password_hash: str,
        machine_label: str = "",
    ) -> HeadClient:
        existing = (
            self
            .get_client_by_login(
                login
            )
        )

        if (
            existing
            is not None
        ):
            raise ValueError(
                "Логин уже "
                "зарегистрирован "
                "на головном "
                "сервере"
            )

        api_key = (
            secrets
            .token_urlsafe(
                32
            )
        )

        with self._connect() as connection:
            cursor = (
                connection
                .execute(
                    """
                    INSERT INTO clients (
                        created_at,
                        full_name,
                        phone,
                        email,
                        birth_date,
                        login,
                        password_hash,
                        api_key,
                        machine_label
                    )
                    VALUES (
                        ?, ?, ?, ?, ?, ?,
                        ?, ?, ?
                    )
                    """,
                    (
                        utc_now_iso(),
                        full_name,
                        phone,
                        email,
                        birth_date,
                        login,
                        password_hash,
                        api_key,
                        machine_label,
                    ),
                )
            )

            client_id = (
                cursor
                .lastrowid
            )

            assert (
                client_id
                is not None
            )

            connection.commit()

        client = (
            self
            .get_client_by_id(
                int(
                    client_id
                )
            )
        )

        assert (
            client
            is not None
        )

        self.get_entitlements(client.id)
        return client

    def get_client_by_id(
        self,
        client_id: int,
    ) -> (
        HeadClient | None
    ):
        with self._connect() as connection:
            row = (
                connection
                .execute(
                    """
                    SELECT *
                    FROM clients
                    WHERE id = ?
                    """,
                    (
                        client_id,
                    ),
                )
                .fetchone()
            )

        if row is None:
            return None

        return (
            self
            ._row_to_client(
                row
            )
        )

    def get_client_by_login(
        self,
        login: str,
    ) -> (
        HeadClient | None
    ):
        with self._connect() as connection:
            row = (
                connection
                .execute(
                    """
                    SELECT *
                    FROM clients
                    WHERE login = ?
                    """,
                    (
                        login,
                    ),
                )
                .fetchone()
            )

        if row is None:
            return None

        return (
            self
            ._row_to_client(
                row
            )
        )

    def get_client_by_api_key(
        self,
        api_key: str,
    ) -> (
        HeadClient | None
    ):
        with self._connect() as connection:
            row = (
                connection
                .execute(
                    """
                    SELECT *
                    FROM clients
                    WHERE api_key = ?
                    """,
                    (
                        api_key,
                    ),
                )
                .fetchone()
            )

        if row is None:
            return None

        return (
            self
            ._row_to_client(
                row
            )
        )

    def list_clients(
        self,
    ) -> list[
        HeadClient
    ]:
        with self._connect() as connection:
            rows = (
                connection
                .execute(
                    """
                    SELECT *
                    FROM clients
                    ORDER BY id
                    """
                )
                .fetchall()
            )

        return [
            self
            ._row_to_client(
                row
            )

            for row
            in rows
        ]

    def set_password_reset_code(
        self,
        client_id: int,
        ttl_seconds: int = 1800,
    ) -> tuple[
        str,
        str,
    ]:
        client = (
            self
            .get_client_by_id(
                client_id
            )
        )

        if (
            client
            is None
        ):
            raise ValueError(
                "Клиент не найден"
            )

        code = (
            str(
                secrets
                .randbelow(
                    1_000_000
                )
            )
            .zfill(6)
        )

        code_hash = (
            hashlib
            .sha256(
                code
                .encode(
                    "utf-8"
                )
            )
            .hexdigest()
        )

        expires_at = (
            datetime
            .now(
                timezone.utc
            )
            + timedelta(
                seconds=(
                    ttl_seconds
                )
            )
        )

        expires_at_iso = (
            expires_at
            .isoformat()
        )

        with self._connect() as connection:
            connection.execute(
                """
                UPDATE clients
                SET
                    password_reset_code_hash = ?,
                    password_reset_expires_at = ?
                WHERE id = ?
                """,
                (
                    code_hash,
                    expires_at_iso,
                    client_id,
                ),
            )

            connection.commit()

        return (
            code,
            expires_at_iso,
        )

    def confirm_password_reset(
        self,
        login: str,
        code: str,
        new_password_hash: str,
    ) -> HeadClient:
        with self._connect() as connection:
            row = (
                connection
                .execute(
                    """
                    SELECT *
                    FROM clients
                    WHERE login = ?
                    """,
                    (
                        login
                        .strip(),
                    ),
                )
                .fetchone()
            )

        if row is None:
            raise ValueError(
                "Пользователь "
                "не найден"
            )

        stored_code_hash = (
            row[
                "password_reset_code_hash"
            ]
        )

        expires_at_raw = (
            row[
                "password_reset_expires_at"
            ]
        )

        if (
            not stored_code_hash
            or not expires_at_raw
        ):
            raise ValueError(
                "Сброс пароля "
                "не запрошен"
            )

        expires_at = (
            datetime
            .fromisoformat(
                expires_at_raw
            )
        )

        if (
            expires_at
            < datetime
            .now(
                timezone.utc
            )
        ):
            raise ValueError(
                "Код сброса "
                "истёк"
            )

        provided_hash = (
            hashlib
            .sha256(
                code
                .strip()
                .encode(
                    "utf-8"
                )
            )
            .hexdigest()
        )

        if (
            not hmac
            .compare_digest(
                provided_hash,
                stored_code_hash,
            )
        ):
            raise ValueError(
                "Неверный код "
                "сброса"
            )

        with self._connect() as connection:
            connection.execute(
                """
                UPDATE clients
                SET
                    password_hash = ?,
                    password_reset_code_hash = NULL,
                    password_reset_expires_at = NULL
                WHERE id = ?
                """,
                (
                    new_password_hash,
                    row[
                        "id"
                    ],
                ),
            )

            connection.commit()

        client = (
            self
            .get_client_by_id(
                int(
                    row[
                        "id"
                    ]
                )
            )
        )

        assert (
            client
            is not None
        )

        return client

    # ----------------------------------------
    # Sync
    # ----------------------------------------

    def store_sync(
        self,
        client_id: int,
        payload: Any,
        device_key: str = "",
    ) -> None:
        serialized = (
            json.dumps(
                payload,

                ensure_ascii=(
                    False
                ),

                sort_keys=(
                    True
                ),
            )
        )

        now = (
            utc_now_iso()
        )

        with self._connect() as connection:
            if device_key:
                connection.execute(
                    "UPDATE devices SET last_sync_payload = ? WHERE client_id = ? AND device_key = ?",
                    (serialized, client_id, device_key),
                )
                rows = connection.execute(
                    "SELECT last_sync_payload FROM devices WHERE client_id = ? AND last_sync_payload IS NOT NULL ORDER BY last_seen_at ASC",
                    (client_id,),
                ).fetchall()
                device_payloads = [json.loads(row[0]) for row in rows]
                accounts = {}
                platforms = set()
                instruments = set()
                for incoming in device_payloads:
                    for account in incoming.get("accounts", []):
                        if isinstance(account, dict):
                            key = (account.get("broker"), account.get("broker_account_id"), account.get("mode"))
                            accounts[key] = account
                    platforms.update(incoming.get("platforms", []))
                    instruments.update(incoming.get("instruments", []))
                merged = dict(payload)
                merged["accounts"] = list(accounts.values())
                merged["platforms"] = sorted(platforms)
                merged["instruments"] = sorted(instruments)
                for field, identity in (("sessions", "session_id"), ("closed_grids", "grid_id")):
                    entries = {}
                    for incoming in device_payloads:
                        for entry in incoming.get(field, []):
                            if isinstance(entry, dict) and entry.get(identity):
                                entries[str(entry[identity])] = entry
                    merged[field] = list(entries.values())
                histories = {}
                for incoming in device_payloads:
                    for entry in incoming.get("balance_history", []):
                        if isinstance(entry, dict):
                            key = (entry.get("trading_account_id"), entry.get("created_at"), entry.get("currency"))
                            histories[key] = entry
                merged["balance_history"] = sorted(histories.values(), key=lambda entry: str(entry.get("created_at") or ""))
                if not accounts:
                    merged.update({field: payload.get(field, "0") for field in ("initial_balance", "current_balance", "total_profit")})
                else:
                    merged["current_balance"] = str(sum((Decimal(str(account.get("current_balance") or account.get("historical_balance") or "0")) for account in accounts.values()), Decimal("0")))
                    merged["total_profit"] = str(sum((Decimal(str(account.get("realized_profit") or "0")) + Decimal(str(account.get("unrealized_profit") or "0")) for account in accounts.values()), Decimal("0")))
                    merged["initial_balance"] = str(sum((Decimal(str(account.get("initial_balance") or "0")) for account in accounts.values()), Decimal("0")))
                latest_serialized = json.dumps(merged, ensure_ascii=False)
            else:
                latest_serialized = serialized
            if isinstance(payload, dict):
                for account in payload.get("accounts", []):
                    if not isinstance(account, dict) or not account.get("broker"):
                        continue
                    for ticker in account.get("instruments", []):
                        if isinstance(ticker, str) and ticker.strip():
                            connection.execute(
                                "INSERT OR IGNORE INTO asset_trading_settings(platform, ticker, updated_at) VALUES (?, ?, ?)",
                                (str(account["broker"]).lower(), ticker.strip().upper(), now),
                            )
            connection.execute(
                """
                INSERT INTO client_syncs (
                    client_id,
                    created_at,
                    payload
                )
                VALUES (?, ?, ?)
                """,
                (
                    client_id,
                    now,
                    serialized,
                ),
            )

            connection.execute(
                """
                UPDATE clients
                SET
                    last_sync_at = ?,
                    latest_payload = ?
                WHERE id = ?
                """,
                (
                    now,
                    latest_serialized,
                    client_id,
                ),
            )

            connection.commit()

    def list_syncs(
        self,
        client_id: int,
        limit: int = 20,
    ) -> list[dict]:
        with self._connect() as connection:
            rows = (
                connection
                .execute(
                    """
                    SELECT
                        id,
                        created_at,
                        payload
                    FROM client_syncs
                    WHERE client_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (
                        client_id,
                        limit,
                    ),
                )
                .fetchall()
            )

        return [
            {
                "id": int(
                    row[
                        "id"
                    ]
                ),

                "created_at": (
                    row[
                        "created_at"
                    ]
                ),

                "payload": (
                    json
                    .loads(
                        row[
                            "payload"
                        ]
                    )
                ),
            }

            for row
            in rows
        ]

    def client_metrics(
        self,
        client: HeadClient,
    ) -> dict:
        """
        Извлекает агрегаты
        из последнего sync-
        payload для списка
        клиентов.
        """

        if (
            client
            .latest_payload
            is None
        ):
            return {}

        try:
            payload = (
                json
                .loads(
                    client
                    .latest_payload
                )
            )

        except Exception:
            return {}

        accounts = (
            payload
            .get(
                "accounts",
                [],
            )
        )

        instruments = (
            payload
            .get(
                "instruments",
                [],
            )
        )

        platforms = (
            payload
            .get(
                "platforms",
                [],
            )
        )

        return {
            "initial_balance": (
                payload
                .get(
                    "initial_balance"
                )
            ),

            "current_balance": (
                payload
                .get(
                    "current_balance"
                )
            ),

            "total_profit": (
                payload
                .get(
                    "total_profit"
                )
            ),

            "roe_percent": (
                payload
                .get(
                    "roe_percent"
                )
            ),

            "accounts_count": (
                len(
                    accounts
                )
            ),

            "account_ids": [
                account
                .get(
                    "broker_account_id"
                )

                for account
                in accounts
            ],

            "platforms": (
                platforms
            ),

            "instruments": (
                instruments
            ),
        }

    @staticmethod
    def _row_to_client(
        row: Any,
    ) -> HeadClient:
        return (
            HeadClient(
                id=int(
                    row[
                        "id"
                    ]
                ),

                created_at=(
                    row[
                        "created_at"
                    ]
                ),

                full_name=(
                    row[
                        "full_name"
                    ]
                ),

                phone=(
                    row[
                        "phone"
                    ]
                ),

                email=(
                    row[
                        "email"
                    ]
                ),

                birth_date=(
                    row[
                        "birth_date"
                    ]
                ),

                login=(
                    row[
                        "login"
                    ]
                ),

                password_hash=(
                    row[
                        "password_hash"
                    ]
                ),

                api_key=(
                    row[
                        "api_key"
                    ]
                ),

                machine_label=(
                    row[
                        "machine_label"
                    ]
                ),

                last_sync_at=(
                    row[
                        "last_sync_at"
                    ]
                ),

                latest_payload=(
                    row[
                        "latest_payload"
                    ]
                ),
            )
        )

    # ----------------------------------------
    # Devices 1.4
    # ----------------------------------------

    def upsert_device(
        self,
        client_id: int,
        device_key: str,
        machine_label: str = "",
        source_address: str | None = None,
        software_endpoint: str | None = None,
    ) -> dict:
        key = (
            device_key
            .strip()
        )

        if (
            not key
        ):
            raise ValueError(
                "Пустой device_key"
            )

        now = (
            utc_now_iso()
        )

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO devices (
                    client_id,
                    device_key,
                    machine_label,
                    created_at,
                    last_seen_at
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(device_key)
                DO UPDATE SET
                    client_id = (
                        excluded.client_id
                    ),
                    machine_label = (
                        excluded.machine_label
                    ),
                    last_seen_at = (
                        excluded.last_seen_at
                    )
                """,
                (
                    client_id,
                    key,
                    machine_label
                    .strip(),
                    now,
                    now,
                ),
            )

            if source_address is not None:
                connection.execute("UPDATE devices SET source_address = ? WHERE device_key = ?", (source_address, key))
            if software_endpoint is not None:
                from urllib.parse import urlsplit

                endpoint = urlsplit(software_endpoint)
                if len(software_endpoint) > 512 or endpoint.scheme not in {"http", "https"} or not endpoint.hostname or endpoint.username or endpoint.password or endpoint.query or endpoint.fragment:
                    raise ValueError("Invalid software endpoint")
                connection.execute("UPDATE devices SET software_endpoint = ? WHERE device_key = ?", (software_endpoint, key))
            row = (
                connection
                .execute(
                    """
                    SELECT *
                    FROM devices
                    WHERE device_key = ?
                    """,
                    (
                        key,
                    ),
                )
                .fetchone()
            )

            assert (
                row
                is not None
            )

            connection.execute(
                """
                INSERT OR IGNORE INTO
                device_daily_activity (
                    day,
                    device_id,
                    created_at
                )
                VALUES (?, ?, ?)
                """,
                (
                    now[:10],
                    int(
                        row[
                            "id"
                        ]
                    ),

                    now,
                ),
            )

            connection.commit()

        return (
            self
            ._row_to_device(
                row
            )
        )

    def list_devices(
        self,
    ) -> list[
        dict
    ]:
        with self._connect() as connection:
            rows = (
                connection
                .execute(
                    """
                    SELECT *
                    FROM devices
                    ORDER BY id
                    """
                )
                .fetchall()
            )

        return [
            self
            ._row_to_device(
                row
            )

            for row
            in rows
        ]

    def set_device_head_flag(
        self,
        device_id: int,
        is_head: bool,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE devices
                SET is_head = ?
                WHERE id = ?
                """,
                (
                    1
                    if is_head

                    else 0,

                    device_id,
                ),
            )

            connection.commit()

    def daily_activity(
        self,
        days: int = 180,
        all_time: bool = False,
    ) -> list[dict]:
        today = datetime.now(timezone.utc).date()
        with self._connect() as connection:
            if all_time:
                first = connection.execute(
                    """
                    SELECT MIN(day) FROM (
                        SELECT DATE(created_at) AS day FROM clients
                        UNION ALL SELECT DATE(created_at) FROM devices
                        UNION ALL SELECT day FROM device_daily_activity
                        UNION ALL SELECT DATE(created_at) FROM client_syncs
                        UNION ALL SELECT DATE(created_at) FROM topup_requests
                    )
                    """
                ).fetchone()[0]
                start_day = min(today, datetime.fromisoformat(first).date()) if first else today
            else:
                start_day = today - timedelta(days=max(1, min(days, 180)) - 1)

            start = start_day.isoformat()
            copies = {
                row["day"]: row["count"]
                for row in connection.execute(
                    """SELECT day, COUNT(*) AS count FROM device_daily_activity
                    WHERE day >= ? AND day <= ? GROUP BY day""",
                    (start, today.isoformat()),
                )
            }
            syncs = {
                row["day"]: row["count"]
                for row in connection.execute(
                    """SELECT DATE(created_at) AS day, COUNT(DISTINCT client_id) AS count
                    FROM client_syncs WHERE created_at >= ? AND created_at < ?
                    GROUP BY DATE(created_at)""",
                    (start, (today + timedelta(days=1)).isoformat()),
                )
            }

            def counts(table: str, column: str) -> dict[str, int]:
                return {
                    row["day"]: row["count"]
                    for row in connection.execute(
                        f"SELECT DATE({column}) AS day, COUNT(*) AS count "
                        f"FROM {table} WHERE {column} >= ? AND {column} < ? "
                        f"GROUP BY DATE({column})",
                        (start, (today + timedelta(days=1)).isoformat()),
                    )
                }

            new_clients = counts("clients", "created_at")
            new_devices = counts("devices", "created_at")
            new_topups = counts("topup_requests", "created_at")
            reviewed_topups = {
                row["day"]: row["count"]
                for row in connection.execute(
                    """SELECT DATE(reviewed_at) AS day, COUNT(*) AS count
                    FROM topup_requests WHERE reviewed_at >= ? AND reviewed_at < ?
                    AND status != 'pending' GROUP BY DATE(reviewed_at)""",
                    (start, (today + timedelta(days=1)).isoformat()),
                )
            }
            clients_total = connection.execute(
                "SELECT COUNT(*) FROM clients WHERE created_at < ?", (start,)
            ).fetchone()[0]
            devices_total = connection.execute(
                "SELECT COUNT(*) FROM devices WHERE created_at < ?", (start,)
            ).fetchone()[0]
            topups_pending = connection.execute(
                """SELECT COUNT(*) FROM topup_requests WHERE created_at < ?
                AND (reviewed_at IS NULL OR reviewed_at >= ? OR status = 'pending')""",
                (start, start),
            ).fetchone()[0]

        daily = []
        for offset in range((today - start_day).days + 1):
            day = (start_day + timedelta(days=offset)).isoformat()
            clients_total += new_clients.get(day, 0)
            devices_total += new_devices.get(day, 0)
            topups_pending += new_topups.get(day, 0) - reviewed_topups.get(day, 0)
            daily.append({
                "day": day,
                "copies": copies.get(day, 0),
                "clients_total": clients_total,
                "clients_active_24h": syncs.get(day, 0),
                "devices_total": devices_total,
                "devices_online": copies.get(day, 0),
                "topups_pending": topups_pending,
            })
        return daily

    def overview_stats(
        self,
    ) -> dict:
        """
        Сводные цифры для вкладки
        «Общее»: клиенты, активность
        устройств, ожидающие
        пополнения.
        """

        now = (
            datetime
            .now(
                timezone.utc
            )
        )

        day_ago = (
            now
            - timedelta(
                hours=24,
            )
        )\
            .isoformat()

        online_window = (
            now
            - timedelta(
                minutes=5,
            )
        )\
            .isoformat()

        with self._connect() as connection:
            clients_total = (
                int(
                    connection
                    .execute(
                        """
                        SELECT COUNT(*)
                        FROM clients
                        """
                    )
                    .fetchone()[
                        0
                    ]
                )
            )

            clients_active_24h = (
                int(
                    connection
                    .execute(
                        """
                        SELECT COUNT(*)
                        FROM clients
                        WHERE last_sync_at
                            IS NOT NULL
                            AND last_sync_at >= ?
                        """,
                        (
                            day_ago,
                        ),
                    )
                    .fetchone()[
                        0
                    ]
                )
            )

            devices_total = (
                int(
                    connection
                    .execute(
                        """
                        SELECT COUNT(*)
                        FROM devices
                        """
                    )
                    .fetchone()[
                        0
                    ]
                )
            )

            devices_online = (
                int(
                    connection
                    .execute(
                        """
                        SELECT COUNT(*)
                        FROM devices
                        WHERE last_seen_at >= ?
                        """,
                        (
                            online_window,
                        ),
                    )
                    .fetchone()[
                        0
                    ]
                )
            )

            topups_pending = (
                int(
                    connection
                    .execute(
                        """
                        SELECT COUNT(*)
                        FROM topup_requests
                        WHERE status = 'pending'
                        """
                    )
                    .fetchone()[
                        0
                    ]
                )
            )

        return {
            "clients_total": (
                clients_total
            ),

            "clients_active_24h": (
                clients_active_24h
            ),

            "devices_total": (
                devices_total
            ),

            "devices_online": (
                devices_online
            ),

            "topups_pending": (
                topups_pending
            ),
        }

    def list_activity_events(
        self,
        limit: int = 50,
    ) -> list[
        dict
    ]:
        """
        Общая лента событий:
        регистрации, включения
        новых копий ПО, заявки
        и решения по пополнениям.
        """

        if (
            limit
            < 1
        ):
            limit = 1

        if (
            limit
            > 500
        ):
            limit = 500

        with self._connect() as connection:
            rows = (
                connection
                .execute(
                    """
                    SELECT
                        event.at,
                        event.type,
                        event.client_id,
                        clients.login
                            AS client_login,
                        clients.full_name
                            AS client_full_name,
                        event.amount,
                        event.details
                    FROM (
                        SELECT created_at AS at,
                            'client_registered' AS type,
                            id AS client_id,
                            NULL AS amount,
                            login AS details
                        FROM clients

                        UNION ALL

                        SELECT created_at AS at,
                            'device_first_seen' AS type,
                            client_id,
                            NULL AS amount,
                            CASE
                                WHEN machine_label != ''
                                THEN machine_label
                                ELSE device_key
                            END AS details
                        FROM devices

                        UNION ALL

                        SELECT created_at AS at,
                            'topup_created' AS type,
                            client_id,
                            amount,
                            comment AS details
                        FROM topup_requests

                        UNION ALL

                        SELECT reviewed_at AS at,
                            CASE status
                                WHEN 'approved'
                                THEN 'topup_approved'
                                ELSE 'topup_rejected'
                            END AS type,
                            client_id,
                            amount,
                            review_note AS details
                        FROM topup_requests
                        WHERE reviewed_at
                            IS NOT NULL
                            AND status IN (
                                'approved',
                                'rejected'
                            )
                    ) AS event
                    LEFT JOIN clients
                        ON clients.id
                            = event.client_id
                    WHERE event.at IS NOT NULL
                    ORDER BY event.at DESC
                    LIMIT ?
                    """,
                    (
                        limit,
                    ),
                )
                .fetchall()
            )

        return [
            {
                "at": (
                    row[
                        "at"
                    ]
                ),

                "type": (
                    row[
                        "type"
                    ]
                ),

                "client_id": (
                    int(
                        row[
                            "client_id"
                        ]
                    )
                ),

                "client_login": (
                    row[
                        "client_login"
                    ]
                ),

                "client_full_name": (
                    row[
                        "client_full_name"
                    ]
                ),

                "amount": (
                    row[
                        "amount"
                    ]
                ),

                "details": (
                    row[
                        "details"
                    ]
                ),
            }

            for row
            in rows
        ]

    @staticmethod
    def _row_to_device(
        row: Any,
    ) -> dict:
        return {
            "id": (
                int(
                    row[
                        "id"
                    ]
                )
            ),

            "client_id": (
                int(
                    row[
                        "client_id"
                    ]
                )
            ),

            "device_key": (
                row[
                    "device_key"
                ]
            ),
            "source_address": row["source_address"],
            "software_endpoint": row["software_endpoint"],
            "reverse_reachability_verified": False,

            "machine_label": (
                row[
                    "machine_label"
                ]
            ),

            "is_head": (
                bool(
                    row[
                        "is_head"
                    ]
                )
            ),

            "created_at": (
                row[
                    "created_at"
                ]
            ),

            "last_seen_at": (
                row[
                    "last_seen_at"
                ]
            ),
        }

    # ----------------------------------------
    # Commission v1.3
    # ----------------------------------------

    def set_commission_percent(
        self,
        client_id: int,
        platform: str,
        percent: Decimal,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO commission_settings (
                    client_id,
                    platform,
                    percent,
                    updated_at
                )
                VALUES (?, ?, ?, ?)
                ON CONFLICT(client_id, platform)
                DO UPDATE SET
                    percent = excluded.percent,
                    updated_at = excluded.updated_at
                """,
                (
                    client_id,
                    platform
                    .strip()
                    .lower(),
                    str(
                        percent
                    ),
                    utc_now_iso(),
                ),
            )

    def get_commission_settings(
        self,
        client_id: int,
    ) -> dict:
        with self._connect() as connection:
            rows = (
                connection
                .execute(
                    """
                    SELECT
                        platform,
                        percent
                    FROM commission_settings
                    WHERE client_id = ?
                    """,
                    (
                        client_id,
                    ),
                )
                .fetchall()
            )

        return {
            str(
                row[
                    "platform"
                ]
            ):
                str(
                    row[
                        "percent"
                    ]
                )

            for row
            in rows
        }

    def list_commission_settings(
        self,
    ) -> list[dict]:
        with self._connect() as connection:
            rows = (
                connection
                .execute(
                    """
                    SELECT
                        client_id,
                        platform,
                        percent,
                        updated_at
                    FROM commission_settings
                    ORDER BY
                        client_id,
                        platform
                    """
                )
                .fetchall()
            )

        return [
            {
                "client_id": (
                    row[
                        "client_id"
                    ]
                ),

                "platform": (
                    row[
                        "platform"
                    ]
                ),

                "percent": (
                    row[
                        "percent"
                    ]
                ),

                "updated_at": (
                    row[
                        "updated_at"
                    ]
                ),
            }

            for row
            in rows
        ]

    def set_trading_settings(
        self,
        platform: str,
        min_profit_percent: Decimal,
        entry_rebound_percent: Decimal,
        trailing_percent: Decimal,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO trading_settings (
                    platform,
                    min_profit_percent,
                    entry_rebound_percent,
                    trailing_percent,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(platform) DO UPDATE SET
                    min_profit_percent = excluded.min_profit_percent,
                    entry_rebound_percent = excluded.entry_rebound_percent,
                    trailing_percent = excluded.trailing_percent,
                    updated_at = excluded.updated_at
                """,
                (
                    platform,
                    str(min_profit_percent),
                    str(entry_rebound_percent),
                    str(trailing_percent),
                    utc_now_iso(),
                ),
            )

    def set_asset_trading_settings(
        self, platform: str, ticker: str,
        min_profit_percent: Decimal | None,
        entry_rebound_percent: Decimal | None,
        trailing_percent: Decimal | None,
        take_profit_percent: Decimal | None = None,
        max_take_profit_percent: Decimal | None = None,
        order_amount_multiplier: Decimal | None = None,
        max_order_amount_multiplier: Decimal | None = None,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO asset_trading_settings (
                    platform, ticker, min_profit_percent, entry_rebound_percent,
                    trailing_percent, updated_at, take_profit_percent, max_take_profit_percent,
                    order_amount_multiplier, max_order_amount_multiplier
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(platform, ticker) DO UPDATE SET
                    min_profit_percent = excluded.min_profit_percent,
                    entry_rebound_percent = excluded.entry_rebound_percent,
                    trailing_percent = excluded.trailing_percent,
                    take_profit_percent = excluded.take_profit_percent,
                    max_take_profit_percent = excluded.max_take_profit_percent,
                    order_amount_multiplier = excluded.order_amount_multiplier,
                    max_order_amount_multiplier = excluded.max_order_amount_multiplier,
                    updated_at = excluded.updated_at
                """,
                (platform.strip().lower(), ticker.strip().upper(),
                 str(min_profit_percent) if min_profit_percent is not None else None,
                 str(entry_rebound_percent) if entry_rebound_percent is not None else None,
                 str(trailing_percent) if trailing_percent is not None else None,
                 utc_now_iso(), str(take_profit_percent) if take_profit_percent is not None else None,
                  str(max_take_profit_percent) if max_take_profit_percent is not None else None,
                  str(order_amount_multiplier) if order_amount_multiplier is not None else None,
                  str(max_order_amount_multiplier) if max_order_amount_multiplier is not None else None),
            )

    def get_asset_trading_settings(self) -> dict[str, dict[str, dict[str, str | None]]]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM asset_trading_settings ORDER BY platform, ticker").fetchall()
        result: dict[str, dict[str, dict[str, str | None]]] = {}
        for row in rows:
            result.setdefault(row["platform"], {})[row["ticker"]] = {
                field: row[field] for field in ("min_profit_percent", "entry_rebound_percent", "trailing_percent", "take_profit_percent", "max_take_profit_percent", "order_amount_multiplier", "max_order_amount_multiplier")
            }
        return result

    def get_trading_settings(self) -> dict[str, dict[str, str]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT platform, min_profit_percent,
                       entry_rebound_percent, trailing_percent
                FROM trading_settings ORDER BY platform
                """
            ).fetchall()
        return {
            str(row["platform"]): {
                "min_profit_percent": str(row["min_profit_percent"]),
                "entry_rebound_percent": str(row["entry_rebound_percent"]),
                "trailing_percent": str(row["trailing_percent"]),
            }
            for row in rows
        }

    def record_commission_charge(
        self,
        client_id: int,
        charge: dict,
        device_key: str = "",
    ) -> None:
        for field in ("trade_profit", "percent", "amount"):
            value = Decimal(str(charge.get(field) or "0"))
            if not value.is_finite() or value < 0:
                raise ValueError(f"Invalid commission {field}")
        source_id = charge.get("id")
        source_key = (
            f"{device_key}:{int(source_id)}"
            if source_id is not None and device_key
            else hashlib.sha256(json.dumps(
                charge, sort_keys=True, ensure_ascii=False,
            ).encode("utf-8")).hexdigest()
        )
        created_at = (
            str(
                charge
                .get(
                    "created_at"
                )
                or utc_now_iso()
            )
        )

        level_index = (
            charge
            .get(
                "level_index"
            )
        )

        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO commission_charges (
                    client_id,
                    created_at,
                    broker,
                    instrument_id,
                    ticker,
                    level_index,
                    trade_profit,
                    percent,
                    amount,
                    balance_after,
                    source_key,
                    device_key,
                    trading_account_id
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    client_id,
                    created_at,
                    str(
                        charge
                        .get(
                            "broker"
                        )
                        or ""
                    ),
                    charge
                    .get(
                        "instrument_id"
                    ),
                    charge
                    .get(
                        "ticker"
                    ),
                    int(
                        level_index
                    )

                    if (
                        level_index
                        is not None
                    )

                    else None,
                    str(
                        charge
                        .get(
                            "trade_profit"
                        )
                        or "0"
                    ),
                    str(
                        charge
                        .get(
                            "percent"
                        )
                        or "0"
                    ),
                    str(
                        charge
                        .get(
                            "amount"
                        )
                        or "0"
                    ),
                    str(
                        charge
                        .get(
                            "balance_after"
                        )
                        or "0"
                    ),
                    source_key,
                    device_key,
                    charge.get("trading_account_id"),
                ),
            )

        self.get_entitlements(client_id)

    def list_commission_charges(
        self,
        client_id: (
            int | None
        ) = None,
        limit: int = 100,
    ) -> list[dict]:
        query = (
            """
            SELECT *
            FROM commission_charges
            """
        )

        params: list = []

        if (
            client_id
            is not None
        ):
            query += (
                " WHERE client_id = ?"
            )

            params.append(
                client_id
            )

        query += (
            " ORDER BY id DESC LIMIT ?"
        )

        params.append(
            limit
        )

        with self._connect() as connection:
            rows = (
                connection
                .execute(
                    query,
                    params,
                )
                .fetchall()
            )

        return [
            {
                "id": (
                    row[
                        "id"
                    ]
                ),

                "client_id": (
                    row[
                        "client_id"
                    ]
                ),

                "created_at": (
                    row[
                        "created_at"
                    ]
                ),

                "broker": (
                    row[
                        "broker"
                    ]
                ),

                "ticker": (
                    row[
                        "ticker"
                    ]
                ),

                "level_index": (
                    row[
                        "level_index"
                    ]
                ),

                "trade_profit": (
                    row[
                        "trade_profit"
                    ]
                ),

                "percent": (
                    row[
                        "percent"
                    ]
                ),

                "amount": (
                    row[
                        "amount"
                    ]
                ),

                "balance_after": (
                    row[
                        "balance_after"
                    ]
                ),
                "trading_account_id": row["trading_account_id"],
                "device_key": row["device_key"],
            }

            for row
            in rows
        ]

    def get_commission_balance(
        self,
        client_id: int,
    ) -> Decimal:
        with self._connect() as connection:
            row = (
                connection
                .execute(
                    """
                    SELECT
                        COALESCE(
                            SUM(amount),
                            0
                        )
                        AS total
                    FROM commission_charges
                    WHERE client_id = ?
                    """,
                    (
                        client_id,
                    ),
                )
                .fetchone()
            )

        charged = (
            Decimal(
                str(
                    row[
                        "total"
                    ]
                )
            )
        )

        return (
            Decimal("0")
            - charged
        )

    def get_entitlements(self, client_id: int) -> dict:
        balance = self.get_commission_balance(client_id)
        with self._connect() as connection:
            connection.execute("INSERT OR IGNORE INTO client_entitlements(client_id) VALUES (?)", (client_id,))
            if balance <= Decimal("-500"):
                connection.execute(
                    "UPDATE client_entitlements SET trial_ended_at = COALESCE(trial_ended_at, ?) WHERE client_id = ?",
                    (utc_now_iso(), client_id),
                )
            row = connection.execute("SELECT * FROM client_entitlements WHERE client_id = ?", (client_id,)).fetchone()
        trial_active = row["trial_ended_at"] is None
        privileged = bool(row["allow_insufficient_balance"])
        return {
            "balance": str(balance), "trial_active": trial_active,
            "trial_ended_at": row["trial_ended_at"],
            "status": "trial" if trial_active else "standard",
            "allow_insufficient_balance": privileged,
            "can_start": privileged or balance > 0 or (trial_active and balance > Decimal("-500")),
        }

    def set_insufficient_balance_permission(self, client_id: int, allowed: bool) -> dict:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO client_entitlements(client_id, allow_insufficient_balance) VALUES (?, ?) "
                "ON CONFLICT(client_id) DO UPDATE SET allow_insufficient_balance = excluded.allow_insufficient_balance",
                (client_id, int(allowed)),
            )
        return self.get_entitlements(client_id)

    def adjust_cabinet_balance(self, client_id: int, target: Decimal, note: str) -> dict:
        if not target.is_finite():
            raise ValueError("Balance must be finite")
        self.get_entitlements(client_id)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute("SELECT amount FROM commission_charges WHERE client_id = ?", (client_id,)).fetchall()
            current = -sum((Decimal(row["amount"]) for row in rows), Decimal("0"))
            connection.execute(
                """
                INSERT INTO commission_charges (
                    client_id, created_at, broker, ticker, trade_profit, percent, amount, balance_after
                ) VALUES (?, ?, 'admin_adjustment', ?, '0', '0', ?, ?)
                """,
                (client_id, utc_now_iso(), note.strip(), str(current - target), str(target)),
            )
        return self.get_entitlements(client_id)

    def record_control_log(
        self,
        client_id: int,
        entry: dict,
    ) -> None:
        """
        Контрольный лог
        клиентской копии
        (сверка ордеров,
        снятие позиций,
        расхождения, ошибки
        сверки). Дубликаты
        по (client_id,
        source_id)
        игнорируются.
        """

        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO
                client_control_logs (
                    client_id,
                    source_id,
                    created_at,
                    trading_account_id,
                    instrument_id,
                    ticker,
                    event_type,
                    details
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    client_id,
                    int(
                        entry
                        .get(
                            "source_id"
                        )
                        or 0
                    ),
                    str(
                        entry
                        .get(
                            "created_at"
                        )
                        or utc_now_iso()
                    ),
                    entry
                    .get(
                        "trading_account_id"
                    ),
                    entry
                    .get(
                        "instrument_id"
                    ),
                    entry
                    .get(
                        "ticker"
                    ),
                    str(
                        entry
                        .get(
                            "event_type"
                        )
                        or ""
                    ),
                    str(
                        entry
                        .get(
                            "details"
                        )
                        or ""
                    ),
                ),
            )

    def list_control_logs(
        self,
        client_id: (
            int | None
        ) = None,
        limit: int = 100,
    ) -> list[dict]:
        query = (
            """
            SELECT *
            FROM client_control_logs
            """
        )

        params: list = []

        if (
            client_id
            is not None
        ):
            query += (
                " WHERE client_id = ?"
            )

            params.append(
                client_id
            )

        query += (
            " ORDER BY id DESC LIMIT ?"
        )

        params.append(
            limit
        )

        with self._connect() as connection:
            rows = (
                connection
                .execute(
                    query,
                    params,
                )
                .fetchall()
            )

        return [
            {
                "id": (
                    row[
                        "id"
                    ]
                ),

                "client_id": (
                    row[
                        "client_id"
                    ]
                ),

                "source_id": (
                    row[
                        "source_id"
                    ]
                ),

                "created_at": (
                    row[
                        "created_at"
                    ]
                ),

                "trading_account_id": (
                    row[
                        "trading_account_id"
                    ]
                ),

                "instrument_id": (
                    row[
                        "instrument_id"
                    ]
                ),

                "ticker": (
                    row[
                        "ticker"
                    ]
                ),

                "event_type": (
                    row[
                        "event_type"
                    ]
                ),

                "details": (
                    row[
                        "details"
                    ]
                ),
            }

            for row in rows
        ]


    # ----------------------------------------
    # Topups B4 (пополнение баланса ЛК)
    # ----------------------------------------

    def create_topup_request(
        self,
        client_id: int,
        amount: Decimal,
        comment: str = "",
        document_name: (
            str | None
        ) = None,
        document_mime: (
            str | None
        ) = None,
        document_data: (
            str | None
        ) = None,
    ) -> dict:
        amount = (
            amount
            .quantize(
                Decimal(
                    "0.01"
                )
            )
        )

        with self._connect() as connection:
            cursor = (
                connection
                .execute(
                    """
                    INSERT INTO topup_requests (
                        client_id,
                        created_at,
                        amount,
                        comment,
                        document_name,
                        document_mime,
                        document_data,
                        status
                    )
                    VALUES (
                        ?, ?, ?, ?, ?, ?, ?,
                        'pending'
                    )
                    """,
                    (
                        client_id,
                        utc_now_iso(),
                        str(
                            amount
                        ),
                        (
                            comment
                            .strip()
                        ),
                        document_name,
                        document_mime,
                        document_data,
                    ),
                )
            )

            request_id = (
                cursor
                .lastrowid
            )

            assert (
                request_id
                is not None
            )

            row = (
                connection
                .execute(
                    """
                    SELECT *
                    FROM topup_requests
                    WHERE id = ?
                    """,
                    (
                        request_id,
                    ),
                )
                .fetchone()
            )

        assert (
            row
            is not None
        )

        return (
            self
            ._row_to_topup(
                row
            )
        )

    def get_topup_request(
        self,
        request_id: int,
        with_document: bool = (
            False
        ),
    ) -> (
        dict | None
    ):
        with self._connect() as connection:
            row = (
                connection
                .execute(
                    """
                    SELECT *
                    FROM topup_requests
                    WHERE id = ?
                    """,
                    (
                        request_id,
                    ),
                )
                .fetchone()
            )

        if row is None:
            return None

        request = (
            self
            ._row_to_topup(
                row
            )
        )

        if with_document:
            request[
                "document_data"
            ] = (
                row[
                    "document_data"
                ]
            )

        return request

    def list_topup_requests(
        self,
        client_id: (
            int | None
        ) = None,
        status: (
            str | None
        ) = None,
        limit: int = 100,
    ) -> list[dict]:
        query = (
            """
            SELECT *
            FROM topup_requests
            """
        )

        conditions: list = []

        params: list = []

        if (
            client_id
            is not None
        ):
            conditions.append(
                "client_id = ?"
            )

            params.append(
                client_id
            )

        if status:
            conditions.append(
                "status = ?"
            )

            params.append(
                status
                .strip()
                .lower()
            )

        if conditions:
            query += (
                " WHERE "
                + " AND "
                .join(
                    conditions
                )
            )

        query += (
            " ORDER BY id DESC "
            "LIMIT ?"
        )

        params.append(
            limit
        )

        with self._connect() as connection:
            rows = (
                connection
                .execute(
                    query,
                    params,
                )
                .fetchall()
            )

        return [
            self
            ._row_to_topup(
                row
            )

            for row in rows
        ]

    def approve_topup_request(
        self,
        request_id: int,
        review_note: str = "",
    ) -> (
        dict | None
    ):
        """
        Подтверждение заявки:
        в комиссионный журнал
        добавляется запись
        topup (отрицательная
        сумма — баланс растёт),
        заявка получает статус
        approved и итоговый
        баланс.
        """

        with self._connect() as connection:
            row = (
                connection
                .execute(
                    """
                    SELECT *
                    FROM topup_requests
                    WHERE id = ?
                    """,
                    (
                        request_id,
                    ),
                )
                .fetchone()
            )

        if row is None:
            return None

        if (
            row[
                "status"
            ]
            != "pending"
        ):
            raise ValueError(
                "Заявка уже "
                "обработана"
            )

        amount = (
            Decimal(
                row[
                    "amount"
                ]
            )
        )

        balance_row = None

        with self._connect() as connection:
            balance_row = (
                connection
                .execute(
                    """
                    SELECT
                        COALESCE(
                            SUM(amount),
                            0
                        )
                        AS total
                    FROM commission_charges
                    WHERE client_id = ?
                    """,
                    (
                        row[
                            "client_id"
                        ],
                    ),
                )
                .fetchone()
            )

        balance = (
            Decimal(
                str(
                    balance_row[
                        "total"
                    ]
                )
            )
            * Decimal(
                "-1"
            )
            + amount
        )

        now = (
            utc_now_iso()
        )

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO commission_charges (
                    client_id,
                    created_at,
                    broker,
                    instrument_id,
                    ticker,
                    level_index,
                    trade_profit,
                    percent,
                    amount,
                    balance_after
                )
                VALUES (
                    ?, ?, 'topup',
                    NULL, NULL, NULL,
                    '0', '0', ?, ?
                )
                """,
                (
                    row[
                        "client_id"
                    ],
                    now,
                    str(
                        -amount
                    ),
                    str(
                        balance
                    ),
                ),
            )

            connection.execute(
                """
                UPDATE topup_requests
                SET
                    status = 'approved',
                    reviewed_at = ?,
                    review_note = ?,
                    balance_after = ?
                WHERE id = ?
                """,
                (
                    now,
                    (
                        review_note
                        .strip()
                    ),
                    str(
                        balance
                    ),
                    request_id,
                ),
            )

        request = (
            self
            .get_topup_request(
                request_id
            )
        )

        assert (
            request
            is not None
        )

        return request

    def reject_topup_request(
        self,
        request_id: int,
        review_note: str = "",
    ) -> (
        dict | None
    ):
        with self._connect() as connection:
            row = (
                connection
                .execute(
                    """
                    SELECT *
                    FROM topup_requests
                    WHERE id = ?
                    """,
                    (
                        request_id,
                    ),
                )
                .fetchone()
            )

        if row is None:
            return None

        if (
            row[
                "status"
            ]
            != "pending"
        ):
            raise ValueError(
                "Заявка уже "
                "обработана"
            )

        with self._connect() as connection:
            connection.execute(
                """
                UPDATE topup_requests
                SET
                    status = 'rejected',
                    reviewed_at = ?,
                    review_note = ?
                WHERE id = ?
                """,
                (
                    utc_now_iso(),
                    (
                        review_note
                        .strip()
                    ),
                    request_id,
                ),
            )

        request = (
            self
            .get_topup_request(
                request_id
            )
        )

        assert (
            request
            is not None
        )

        return request

    @staticmethod
    def _row_to_topup(
        row: Any,
    ) -> dict:
        return {
            "id": (
                int(
                    row[
                        "id"
                    ]
                )
            ),

            "client_id": (
                int(
                    row[
                        "client_id"
                    ]
                )
            ),

            "created_at": (
                row[
                    "created_at"
                ]
            ),

            "amount": (
                row[
                    "amount"
                ]
            ),

            "comment": (
                row[
                    "comment"
                ]
            ),

            "document_name": (
                row[
                    "document_name"
                ]
            ),

            "document_mime": (
                row[
                    "document_mime"
                ]
            ),

            "status": (
                row[
                    "status"
                ]
            ),

            "reviewed_at": (
                row[
                    "reviewed_at"
                ]
            ),

            "review_note": (
                row[
                    "review_note"
                ]
            ),

            "balance_after": (
                row[
                    "balance_after"
                ]
            ),
        }


def default_db_path() -> str:
    env_path = (
        os.getenv(
            "HEAD_DB_PATH"
        )
    )

    if env_path:
        return (
            env_path
            .strip()
        )

    return str(
        Path(
            "data"
        )
        / DEFAULT_DB_NAME
    )
