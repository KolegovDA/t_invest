from __future__ import annotations

import sqlite3
from sqlite_schema import SchemaConnection

from dataclasses import dataclass

from datetime import datetime

from pathlib import Path

from domain.platform_connection import (
    PlatformConnection,
)
from domain.trading_account import (
    BrokerType,
    TradingAccountMode,
)


@dataclass(slots=True)
class StoredPlatformConnection:
    platform: PlatformConnection

    protected_credentials: str


@dataclass(slots=True)
class PlatformConnectionRepository:
    db_path: str

    def __post_init__(
        self,
    ) -> None:
        self._ensure_database()

    def _connect(
        self,
    ) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.db_path,
            factory=SchemaConnection,
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
                platform_connections (
                    id TEXT PRIMARY KEY,

                    broker TEXT NOT NULL,

                    mode TEXT NOT NULL,

                    protected_credentials
                        TEXT NOT NULL,

                    created_at TEXT NOT NULL,

                    updated_at TEXT NOT NULL
                )
                """
            )

            connection.execute(
                """
                CREATE UNIQUE INDEX
                IF NOT EXISTS
                idx_platform_connections_unique
                ON platform_connections (
                    broker,
                    mode
                )
                """
            )

            connection.commit()

    def save(
        self,
        platform: PlatformConnection,
        protected_credentials: str,
    ) -> None:
        if (
            platform.created_at
            is None
        ):
            raise ValueError(
                "created_at is required"
            )

        if (
            platform.updated_at
            is None
        ):
            raise ValueError(
                "updated_at is required"
            )

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO
                    platform_connections (
                    id,
                    broker,
                    mode,
                    protected_credentials,
                    created_at,
                    updated_at
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?
                )

                ON CONFLICT(id)
                DO UPDATE SET
                    broker =
                        excluded.broker,

                    mode =
                        excluded.mode,

                    protected_credentials =
                        excluded
                            .protected_credentials,

                    updated_at =
                        excluded.updated_at
                """,

                (
                    platform.id,
                    platform
                    .broker
                    .value,
                    platform
                    .mode
                    .value,
                    protected_credentials,
                    platform
                    .created_at
                    .isoformat(),
                    platform
                    .updated_at
                    .isoformat(),
                ),
            )

            connection.commit()

    def get(
        self,
        platform_id: str,
    ) -> StoredPlatformConnection | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM platform_connections
                WHERE id = ?
                """,

                (
                    platform_id,
                ),
            ).fetchone()

        if row is None:
            return None

        return self._from_row(
            row
        )

    def get_all(
        self,
    ) -> list[
        StoredPlatformConnection
    ]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM platform_connections
                ORDER BY
                    created_at ASC
                """
            ).fetchall()

        return [
            self._from_row(
                row
            )

            for row
            in rows
        ]

    def delete(
        self,
        platform_id: str,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                DELETE FROM
                    platform_connections
                WHERE id = ?
                """,

                (
                    platform_id,
                ),
            )

            connection.commit()

    def exists_for(
        self,
        broker: BrokerType,
        mode: TradingAccountMode,
        exclude_id: (
            str | None
        ) = None,
    ) -> bool:
        query = """
            SELECT id
            FROM platform_connections
            WHERE
                broker = ?
                AND mode = ?
        """

        parameters: list[
            object
        ] = [
            broker.value,
            mode.value,
        ]

        if (
            exclude_id
            is not None
        ):
            query += (
                " AND id != ?"
            )

            parameters.append(
                exclude_id
            )

        with self._connect() as connection:
            row = connection.execute(
                query,

                tuple(
                    parameters
                ),
            ).fetchone()

        return (
            row is not None
        )

    def _from_row(
        self,
        row: sqlite3.Row,
    ) -> StoredPlatformConnection:
        platform = (
            PlatformConnection(
                id=row["id"],

                broker=BrokerType(
                    row[
                        "broker"
                    ]
                ),

                mode=(
                    TradingAccountMode(
                        row[
                            "mode"
                        ]
                    )
                ),

                created_at=(
                    datetime
                    .fromisoformat(
                        row[
                            "created_at"
                        ]
                    )
                ),

                updated_at=(
                    datetime
                    .fromisoformat(
                        row[
                            "updated_at"
                        ]
                    )
                ),
            )
        )

        return StoredPlatformConnection(
            platform=platform,

            protected_credentials=(
                row[
                    "protected_credentials"
                ]
            ),
        )
