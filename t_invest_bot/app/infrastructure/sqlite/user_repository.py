from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class StoredUser:
    id: int
    full_name: str
    phone: str
    email: str
    birth_date: str
    login: str
    password_hash: str
    created_at: str
    head_api_key: (
        str | None
    ) = None


@dataclass(slots=True)
class StoredDevice:
    device_id: str
    user_id: int
    pin_hash: str | None
    biometric_credential_id: (
        str | None
    )
    created_at: str
    last_seen_at: str


@dataclass(slots=True)
class StoredSession:
    token: str
    user_id: int
    device_id: str
    created_at: str
    last_activity: str


@dataclass(slots=True)
class SQLiteUserRepository:
    db_path: str

    def __post_init__(self) -> None:
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
                users (
                    id INTEGER PRIMARY KEY
                        AUTOINCREMENT,
                    full_name TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    email TEXT NOT NULL,
                    birth_date TEXT NOT NULL,
                    login TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                        DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS
                auth_devices (
                    device_id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    pin_hash TEXT,
                    biometric_credential_id TEXT,
                    created_at TEXT NOT NULL
                        DEFAULT CURRENT_TIMESTAMP,
                    last_seen_at TEXT NOT NULL
                        DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS
                auth_sessions (
                    token TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    device_id TEXT NOT NULL,
                    created_at TEXT NOT NULL
                        DEFAULT CURRENT_TIMESTAMP,
                    last_activity TEXT NOT NULL
                        DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            self._ensure_column(
                connection,
                "users",
                "head_api_key",
                "TEXT",
            )

            connection.commit()

    @staticmethod
    def _ensure_column(
        connection,
        table: str,
        column: str,
        ddl_type: str,
    ) -> None:
        columns = {
            row[
                1
            ]

            for row
            in (
                connection
                .execute(
                    f"""
                    PRAGMA table_info(
                        {table}
                    )
                    """
                )
                .fetchall()
            )
        }

        if (
            column
            not in columns
        ):
            connection.execute(
                f"""
                ALTER TABLE {table}
                ADD COLUMN {column}
                    {ddl_type}
                """
            )

    # ----------------------------------------
    # Users
    # ----------------------------------------

    def create_user(
        self,
        full_name: str,
        phone: str,
        email: str,
        birth_date: str,
        login: str,
        password_hash: str,
    ) -> StoredUser:
        with self._connect() as connection:
            cursor = (
                connection
                .execute(
                    """
                    INSERT INTO users (
                        full_name,
                        phone,
                        email,
                        birth_date,
                        login,
                        password_hash
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        full_name,
                        phone,
                        email,
                        birth_date,
                        login,
                        password_hash,
                    ),
                )
            )

            user_id = (
                cursor
                .lastrowid
            )

            connection.commit()

        user = (
            self
            .get_user_by_id(
                int(
                    user_id
                )
            )
        )

        assert (
            user
            is not None
        )

        return user

    def get_user_by_id(
        self,
        user_id: int,
    ) -> (
        StoredUser | None
    ):
        with self._connect() as connection:
            row = (
                connection
                .execute(
                    """
                    SELECT *
                    FROM users
                    WHERE id = ?
                    """,
                    (
                        user_id,
                    ),
                )
                .fetchone()
            )

        if row is None:
            return None

        return (
            self
            ._row_to_user(
                row
            )
        )

    def get_user_by_login(
        self,
        login: str,
    ) -> (
        StoredUser | None
    ):
        with self._connect() as connection:
            row = (
                connection
                .execute(
                    """
                    SELECT *
                    FROM users
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
            ._row_to_user(
                row
            )
        )

    def count_users(
        self,
    ) -> int:
        with self._connect() as connection:
            row = (
                connection
                .execute(
                    """
                    SELECT COUNT(*) AS total
                    FROM users
                    """
                )
                .fetchone()
            )

        return int(
            row[
                "total"
            ]
        )

    def set_user_head_api_key(
        self,
        user_id: int,
        api_key: (
            str | None
        ),
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE users
                SET head_api_key = ?
                WHERE id = ?
                """,
                (
                    api_key,
                    user_id,
                ),
            )

            connection.commit()

    def get_user_head_api_key(
        self,
        user_id: int,
    ) -> (
        str | None
    ):
        with self._connect() as connection:
            row = (
                connection
                .execute(
                    """
                    SELECT head_api_key
                    FROM users
                    WHERE id = ?
                    """,
                    (
                        user_id,
                    ),
                )
                .fetchone()
            )

        if row is None:
            return None

        return (
            row[
                "head_api_key"
            ]
        )

    # ----------------------------------------
    # Devices
    # ----------------------------------------

    def upsert_device(
        self,
        device_id: str,
        user_id: int,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO auth_devices (
                    device_id,
                    user_id
                )
                VALUES (?, ?)

                ON CONFLICT(device_id)
                DO UPDATE SET
                    user_id =
                        excluded.user_id,

                    last_seen_at =
                        CURRENT_TIMESTAMP
                """,
                (
                    device_id,
                    user_id,
                ),
            )

            connection.commit()

    def get_device(
        self,
        device_id: str,
    ) -> (
        StoredDevice | None
    ):
        with self._connect() as connection:
            row = (
                connection
                .execute(
                    """
                    SELECT *
                    FROM auth_devices
                    WHERE device_id = ?
                    """,
                    (
                        device_id,
                    ),
                )
                .fetchone()
            )

        if row is None:
            return None

        return (
            StoredDevice(
                device_id=(
                    row[
                        "device_id"
                    ]
                ),

                user_id=int(
                    row[
                        "user_id"
                    ]
                ),

                pin_hash=(
                    row[
                        "pin_hash"
                    ]
                ),

                biometric_credential_id=(
                    row[
                        "biometric_credential_id"
                    ]
                ),

                created_at=(
                    row[
                        "created_at"
                    ]
                ),

                last_seen_at=(
                    row[
                        "last_seen_at"
                    ]
                ),
            )
        )

    def set_device_pin(
        self,
        device_id: str,
        pin_hash: (
            str | None
        ),
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE auth_devices
                SET pin_hash = ?
                WHERE device_id = ?
                """,
                (
                    pin_hash,
                    device_id,
                ),
            )

            connection.commit()

    def set_device_biometric(
        self,
        device_id: str,
        credential_id: (
            str | None
        ),
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE auth_devices
                SET
                    biometric_credential_id
                        = ?
                WHERE device_id = ?
                """,
                (
                    credential_id,
                    device_id,
                ),
            )

            connection.commit()

    # ----------------------------------------
    # Sessions
    # ----------------------------------------

    def create_session(
        self,
        token: str,
        user_id: int,
        device_id: str,
        created_at: str,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO auth_sessions (
                    token,
                    user_id,
                    device_id,
                    created_at,
                    last_activity
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    token,
                    user_id,
                    device_id,
                    created_at,
                    created_at,
                ),
            )

            connection.commit()

    def get_session(
        self,
        token: str,
    ) -> (
        StoredSession | None
    ):
        with self._connect() as connection:
            row = (
                connection
                .execute(
                    """
                    SELECT *
                    FROM auth_sessions
                    WHERE token = ?
                    """,
                    (
                        token,
                    ),
                )
                .fetchone()
            )

        if row is None:
            return None

        return (
            StoredSession(
                token=(
                    row[
                        "token"
                    ]
                ),

                user_id=int(
                    row[
                        "user_id"
                    ]
                ),

                device_id=(
                    row[
                        "device_id"
                    ]
                ),

                created_at=(
                    row[
                        "created_at"
                    ]
                ),

                last_activity=(
                    row[
                        "last_activity"
                    ]
                ),
            )
        )

    def touch_session(
        self,
        token: str,
        last_activity: str,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE auth_sessions
                SET last_activity = ?
                WHERE token = ?
                """,
                (
                    last_activity,
                    token,
                ),
            )

            connection.commit()

    def delete_session(
        self,
        token: str,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                DELETE FROM auth_sessions
                WHERE token = ?
                """,
                (
                    token,
                ),
            )

            connection.commit()

    @staticmethod
    def _row_to_user(
        row: Any,
    ) -> StoredUser:
        return (
            StoredUser(
                id=int(
                    row[
                        "id"
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

                created_at=(
                    row[
                        "created_at"
                    ]
                ),

                head_api_key=(
                    row[
                        "head_api_key"
                    ]
                ),
            )
        )
