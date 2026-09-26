from __future__ import annotations

import json
import os
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import (
    datetime,
    timezone,
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
                self.db_path
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
                    latest_payload TEXT
                )
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

            connection.commit()

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

    # ----------------------------------------
    # Sync
    # ----------------------------------------

    def store_sync(
        self,
        client_id: int,
        payload: Any,
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
                    serialized,
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
