from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlite_schema import SchemaConnection


@dataclass(slots=True)
class PushSubscriptionRepository:
    db_path: str

    def __post_init__(self) -> None:
        self._ensure_database()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, factory=SchemaConnection)
        connection.row_factory = sqlite3.Row
        return connection

    def _ensure_database(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS push_subscriptions (
                    endpoint TEXT PRIMARY KEY,
                    subscription_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    user_id INTEGER,
                    device_id TEXT
                )
                """
            )

    def save(self, subscription: dict, user_id: int, device_id: str) -> None:
        endpoint = subscription["endpoint"]
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO push_subscriptions (
                    endpoint, subscription_json, created_at, user_id, device_id
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(endpoint) DO UPDATE SET
                    subscription_json = excluded.subscription_json,
                    user_id = excluded.user_id,
                    device_id = excluded.device_id
                WHERE (push_subscriptions.user_id IS NULL
                       AND push_subscriptions.device_id IS NULL)
                   OR (push_subscriptions.user_id = excluded.user_id
                       AND push_subscriptions.device_id = excluded.device_id)
                """,
                (endpoint, json.dumps(subscription), datetime.now(timezone.utc).isoformat(), user_id, device_id),
            )
            if cursor.rowcount == 0:
                raise ValueError("Push subscription belongs to another device")

    def get_all(self, user_id: int | None = None, device_id: str | None = None) -> list[dict]:
        query = "SELECT subscription_json FROM push_subscriptions WHERE user_id IS NOT NULL AND device_id IS NOT NULL"
        parameters: list[int | str] = []
        if user_id is not None:
            query += " AND user_id = ?"
            parameters.append(user_id)
        if device_id is not None:
            query += " AND device_id = ?"
            parameters.append(device_id)
        with self._connect() as connection:
            rows = connection.execute(query + " ORDER BY created_at ASC", parameters).fetchall()
        return [json.loads(row["subscription_json"]) for row in rows]

    def delete(self, endpoint: str, user_id: int | None = None, device_id: str | None = None) -> None:
        query = "DELETE FROM push_subscriptions WHERE endpoint = ?"
        parameters: list[int | str] = [endpoint]
        if user_id is not None:
            query += " AND user_id = ?"
            parameters.append(user_id)
        if device_id is not None:
            query += " AND device_id = ?"
            parameters.append(device_id)
        with self._connect() as connection:
            connection.execute(query, parameters)

    def count(self) -> int:
        with self._connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS total FROM push_subscriptions").fetchone()
        return int(row["total"])
