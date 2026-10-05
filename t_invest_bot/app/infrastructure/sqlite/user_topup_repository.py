from __future__ import annotations

import sqlite3
from sqlite_schema import SchemaConnection

from dataclasses import (
    dataclass,
)

from pathlib import Path


@dataclass(slots=True)
class UserTopupRepository:
    """
    B4: локальные копии заявок
    на пополнение баланса ЛК
    (созданы через головной
    сервер). Статусы обновляются
    при опросе головы; approved
    заявки применяются к балансу
    один раз (applied=1).
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
                user_topup_requests (
                    id INTEGER PRIMARY KEY
                        AUTOINCREMENT,
                    head_request_id INTEGER
                        NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    amount TEXT NOT NULL,
                    comment TEXT NOT NULL
                        DEFAULT '',
                    document_name TEXT,
                    status TEXT NOT NULL
                        DEFAULT 'pending',
                    review_note TEXT,
                    reviewed_at TEXT,
                    applied INTEGER NOT NULL
                        DEFAULT 0
                )
                """
            )

    def upsert_from_head(
        self,
        request: dict,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO user_topup_requests (
                    head_request_id,
                    created_at,
                    amount,
                    comment,
                    document_name,
                    status,
                    review_note,
                    reviewed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(head_request_id)
                DO UPDATE SET
                    status = (
                        excluded.status
                    ),
                    review_note = (
                        excluded.review_note
                    ),
                    reviewed_at = (
                        excluded.reviewed_at
                    )
                """,
                (
                    int(
                        request
                        .get(
                            "id"
                        )
                        or 0
                    ),

                    str(
                        request
                        .get(
                            "created_at"
                        )
                        or ""
                    ),

                    str(
                        request
                        .get(
                            "amount"
                        )
                        or "0"
                    ),

                    str(
                        request
                        .get(
                            "comment"
                        )
                        or ""
                    ),

                    request
                    .get(
                        "document_name"
                    ),

                    str(
                        request
                        .get(
                            "status"
                        )
                        or "pending"
                    ),

                    request
                    .get(
                        "review_note"
                    ),

                    request
                    .get(
                        "reviewed_at"
                    ),
                ),
            )

    def get_by_head_id(
        self,
        head_request_id: int,
    ) -> (
        dict | None
    ):
        with self._connect() as connection:
            row = (
                connection
                .execute(
                    """
                    SELECT *
                    FROM user_topup_requests
                    WHERE head_request_id = ?
                    """,
                    (
                        head_request_id,
                    ),
                )
                .fetchone()
            )

        if row is None:
            return None

        return (
            self
            ._row_to_request(
                row
            )
        )

    def list_recent(
        self,
        limit: int = 20,
    ) -> list[dict]:
        with self._connect() as connection:
            rows = (
                connection
                .execute(
                    """
                    SELECT *
                    FROM user_topup_requests
                    ORDER BY head_request_id
                        DESC
                    LIMIT ?
                    """,
                    (
                        limit,
                    ),
                )
                .fetchall()
            )

        return [
            self
            ._row_to_request(
                row
            )

            for row in rows
        ]

    def mark_applied(
        self,
        head_request_id: int,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE user_topup_requests
                SET applied = 1
                WHERE head_request_id = ?
                """,
                (
                    head_request_id,
                ),
            )

    def list_unapplied_approved(
        self,
    ) -> list[dict]:
        with self._connect() as connection:
            rows = (
                connection
                .execute(
                    """
                    SELECT *
                    FROM user_topup_requests
                    WHERE status = 'approved'
                        AND applied = 0
                    ORDER BY head_request_id
                        ASC
                    """
                )
                .fetchall()
            )

        return [
            self
            ._row_to_request(
                row
            )

            for row in rows
        ]

    @staticmethod
    def _row_to_request(
        row,
    ) -> dict:
        return {
            "id": (
                int(
                    row[
                        "head_request_id"
                    ]
                )
            ),

            "head_request_id": (
                int(
                    row[
                        "head_request_id"
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

            "status": (
                row[
                    "status"
                ]
            ),

            "review_note": (
                row[
                    "review_note"
                ]
            ),

            "reviewed_at": (
                row[
                    "reviewed_at"
                ]
            ),

            "applied": (
                bool(
                    row[
                        "applied"
                    ]
                )
            ),
        }
