from __future__ import annotations

import sqlite3
from sqlite_schema import SchemaConnection
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from infrastructure.security.field_encryption import (
    make_field_cipher,
)


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

    field_cipher: (
        Any | None
    ) = None

    def __post_init__(self) -> None:
        self._ensure_database()

        if (
            self.field_cipher
            is None
        ):
            self.field_cipher = (
                make_field_cipher()
            )

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

        self._encrypt_legacy_fields()

    def _encrypt_legacy_fields(
        self,
    ) -> None:
        """
        v1.3 (п. 4): разовое
        DPAPI-шифрование паролей
        и api-ключей, записанных
        до включения шифрования.
        """

        cipher = (
            self.field_cipher
        )

        if (
            cipher
            is None
        ):
            return

        try:
            with self._connect() as connection:
                rows = (
                    connection
                    .execute(
                        """
                        SELECT
                            id,
                            password_hash,
                            head_api_key
                        FROM users
                        """
                    )
                    .fetchall()
                )

                for row in rows:
                    updates = {}

                    password_hash = (
                        row[
                            "password_hash"
                        ]
                    )

                    if (
                        password_hash
                        and not (
                            cipher
                            .is_encrypted(
                                password_hash
                            )
                        )
                    ):
                        updates[
                            "password_hash"
                        ] = (
                            cipher
                            .encrypt(
                                password_hash
                            )
                        )

                    head_api_key = (
                        row[
                            "head_api_key"
                        ]
                    )

                    if (
                        head_api_key
                        and not (
                            cipher
                            .is_encrypted(
                                head_api_key
                            )
                        )
                    ):
                        updates[
                            "head_api_key"
                        ] = (
                            cipher
                            .encrypt(
                                head_api_key
                            )
                        )

                    if not updates:
                        continue

                    assignments = (
                        ", ".join(
                            f"{column} = ?"

                            for column
                            in updates
                        )
                    )

                    connection.execute(
                        f"""
                        UPDATE users
                        SET {assignments}
                        WHERE id = ?
                        """,
                        (
                            *updates
                            .values(),

                            row[
                                "id"
                            ],
                        ),
                    )

                connection.commit()

        except Exception as error:
            print(
                "USER FIELDS ENCRYPTION ERROR:",
                repr(
                    error
                ),
            )

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
        stored_hash = (
            self
            .field_cipher
            .encrypt(
                password_hash
            )
            if (
                self
                .field_cipher
                is not None
            )

            else password_hash
        )

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
                        stored_hash,
                    ),
                )
            )

            user_id = (
                cursor
                .lastrowid
            )

            connection.commit()

        if user_id is None:
            raise RuntimeError("users insert failed")

        user = (
            self
            .get_user_by_id(
                user_id
            )
        )

        assert (
            user
            is not None
        )

        return user

    def update_user_profile(
        self,
        user_id: int,
        full_name: (
            str | None
        ) = None,
        phone: (
            str | None
        ) = None,
        email: (
            str | None
        ) = None,
        birth_date: (
            str | None
        ) = None,
    ) -> None:
        updates = {}

        if (
            full_name
            is not None
        ):
            updates[
                "full_name"
            ] = (
                full_name
                .strip()
            )

        if (
            phone
            is not None
        ):
            updates[
                "phone"
            ] = (
                phone
                .strip()
            )

        if (
            email
            is not None
        ):
            updates[
                "email"
            ] = (
                email
                .strip()
            )

        if (
            birth_date
            is not None
        ):
            updates[
                "birth_date"
            ] = (
                birth_date
                .strip()
            )

        if (
            not updates
        ):
            return

        set_clause = (
            ", "
            .join(
                f"{column} = ?"

                for column
                in updates
            )
        )

        with self._connect() as connection:
            connection.execute(
                f"""
                UPDATE users
                SET {set_clause}
                WHERE id = ?
                """,
                (
                    *updates
                    .values(),

                    user_id,
                ),
            )

            connection.commit()

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

    def get_first_user_with_head_api_key(self) -> StoredUser | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM users
                WHERE head_api_key IS NOT NULL AND head_api_key != ''
                ORDER BY id
                LIMIT 1
                """,
            ).fetchone()
        return self._row_to_user(row) if row is not None else None

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
        stored_key = (
            api_key
        )

        if (
            api_key
            and (
                self
                .field_cipher
                is not None
            )
        ):
            stored_key = (
                self
                .field_cipher
                .encrypt(
                    api_key
                )
            )

        with self._connect() as connection:
            connection.execute(
                """
                UPDATE users
                SET head_api_key = ?
                WHERE id = ?
                """,
                (
                    stored_key,
                    user_id,
                ),
            )

            connection.commit()

    def set_user_password_hash(
        self,
        user_id: int,
        password_hash: str,
    ) -> None:
        stored_hash = (
            self
            .field_cipher
            .encrypt(
                password_hash
            )

            if (
                self
                .field_cipher
                is not None
            )

            else password_hash
        )

        with self._connect() as connection:
            connection.execute(
                """
                UPDATE users
                SET password_hash = ?
                WHERE id = ?
                """,
                (
                    stored_hash,
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

        value = (
            row[
                "head_api_key"
            ]
        )

        if (
            value
            is None
        ):
            return None

        if (
            self
            .field_cipher
            is None
        ):
            return value

        return (
            self
            .field_cipher
            .decrypt(
                value
            )
        )

    def list_users_without_head_api_key(
        self,
    ) -> (
        list[
            StoredUser
        ]
    ):
        """
        Офлайн-очередь регистрации:
        пользователи, чьи данные
        ещё не доставлены на
        головной сервер.
        """

        with self._connect() as connection:
            rows = (
                connection
                .execute(
                    """
                    SELECT *
                    FROM users
                    WHERE head_api_key IS NULL
                    ORDER BY id
                    """
                )
                .fetchall()
            )

        return [
            self
            ._row_to_user(
                row
            )

            for row
            in rows
        ]

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

    def browser_devices_for_head(self, api_key: str) -> list[dict]:
        user = self.get_first_user_with_head_api_key()
        if user is None or user.head_api_key != api_key:
            return []
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT device_id, MAX(last_activity) AS last_seen_at "
                "FROM auth_sessions WHERE user_id = ? "
                "GROUP BY device_id ORDER BY last_seen_at DESC LIMIT 100",
                (user.id,),
            ).fetchall()
        return [{"device_id": row["device_id"], "last_seen_at": row["last_seen_at"]} for row in rows]

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

    def _row_to_user(
        self,
        row: Any,
    ) -> StoredUser:
        cipher = (
            self
            .field_cipher
        )

        password_hash = (
            row[
                "password_hash"
            ]
        )

        head_api_key = (
            row[
                "head_api_key"
            ]
        )

        if (
            cipher
            is not None
        ):
            password_hash = (
                cipher
                .decrypt(
                    password_hash
                )
            )

            head_api_key = (
                cipher
                .decrypt(
                    head_api_key
                )
            )

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
                    password_hash
                ),

                created_at=(
                    row[
                        "created_at"
                    ]
                ),

                head_api_key=(
                    head_api_key
                ),
            )
        )
