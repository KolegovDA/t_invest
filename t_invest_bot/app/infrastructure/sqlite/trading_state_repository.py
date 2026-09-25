from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from domain.trading_state import (
    TradingSessionState,
)


@dataclass(slots=True)
class TradingStateRepository:
    db_path: str

    def __post_init__(self) -> None:
        self._ensure_database()

    def _connect(
        self,
    ) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.db_path
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

        if path.parent != Path("."):
            path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS
                trading_state_snapshots (
                    session_id TEXT PRIMARY KEY,
                    trading_account_id TEXT NOT NULL,
                    broker_account_id TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    status TEXT NOT NULL,
                    schema_version INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                        DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_trading_state_account
                ON trading_state_snapshots (
                    trading_account_id
                )
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_trading_state_status
                ON trading_state_snapshots (
                    status
                )
                """
            )

            connection.commit()

    def save(
        self,
        state: TradingSessionState,
    ) -> None:
        payload_json = json.dumps(
            state.to_dict(),
            ensure_ascii=False,
            separators=(
                ",",
                ":",
            ),
        )

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO
                trading_state_snapshots (
                    session_id,
                    trading_account_id,
                    broker_account_id,
                    mode,
                    status,
                    schema_version,
                    payload_json,
                    updated_at
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?,
                    CURRENT_TIMESTAMP
                )

                ON CONFLICT(session_id)
                DO UPDATE SET
                    trading_account_id =
                        excluded.trading_account_id,
                    broker_account_id =
                        excluded.broker_account_id,
                    mode =
                        excluded.mode,
                    status =
                        excluded.status,
                    schema_version =
                        excluded.schema_version,
                    payload_json =
                        excluded.payload_json,
                    updated_at =
                        CURRENT_TIMESTAMP
                """,
                (
                    state.session_id,
                    state.trading_account_id,
                    state.broker_account_id,
                    state.mode,
                    state.status,
                    state.schema_version,
                    payload_json,
                ),
            )

            connection.commit()

    def get(
        self,
        session_id: str,
    ) -> TradingSessionState | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT payload_json
                FROM trading_state_snapshots
                WHERE session_id = ?
                """,
                (
                    session_id,
                ),
            ).fetchone()

        if row is None:
            return None

        data = json.loads(
            row[
                "payload_json"
            ]
        )

        return (
            TradingSessionState
            .from_dict(
                data
            )
        )

    def get_active(
        self,
    ) -> list[
        TradingSessionState
    ]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT payload_json
                FROM trading_state_snapshots
                WHERE status IN (
                    'ACTIVE',
                    'RUNNING',
                    'RECOVERY',
                    'DRAINING'
                )
                ORDER BY updated_at DESC
                """
            ).fetchall()

        return [
            TradingSessionState.from_dict(
                json.loads(
                    row[
                        "payload_json"
                    ]
                )
            )
            for row in rows
        ]

    def delete(
        self,
        session_id: str,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                DELETE FROM
                    trading_state_snapshots
                WHERE session_id = ?
                """,
                (
                    session_id,
                ),
            )

            connection.commit()
