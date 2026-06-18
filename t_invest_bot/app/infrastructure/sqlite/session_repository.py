from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from infrastructure.sqlite.sqlite_database import SQLiteDatabase
from strategy.grid_engine import GridLevel, GridLevelStatus


@dataclass(slots=True)
class SQLiteSessionRepository:
    database: SQLiteDatabase

    def save_session(
        self,
        session_id: str,
        account_id: str,
        ticker: str,
        instrument_id: str,
        status: str,
        created_at: datetime,
        levels: list[GridLevel],
    ) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO sessions (
                    id,
                    account_id,
                    ticker,
                    instrument_id,
                    status,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    account_id,
                    ticker,
                    instrument_id,
                    status,
                    created_at.isoformat(),
                ),
            )

            connection.execute(
                """
                DELETE FROM levels
                WHERE session_id = ?
                """,
                (session_id,),
            )

            connection.executemany(
                """
                INSERT INTO levels (
                    session_id,
                    level_index,
                    price,
                    status
                )
                VALUES (?, ?, ?, ?)
                """,
                [
                    (
                        session_id,
                        level.index,
                        str(level.price),
                        level.status.value,
                    )
                    for level in levels
                ],
            )

    def load_session(
        self,
        session_id: str,
    ):
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT
                    id,
                    account_id,
                    ticker,
                    instrument_id,
                    status,
                    created_at
                FROM sessions
                WHERE id = ?
                """,
                (session_id,),
            ).fetchone()

        if row is None:
            raise ValueError(
                f"Session not found: {session_id}"
            )

        return row

    def load_all_sessions(self):
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    id,
                    account_id,
                    ticker,
                    instrument_id,
                    status,
                    created_at
                FROM sessions
                ORDER BY created_at
                """
            ).fetchall()

        return rows

    def load_levels(
        self,
        session_id: str,
    ) -> list[GridLevel]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT level_index, price, status
                FROM levels
                WHERE session_id = ?
                ORDER BY level_index
                """,
                (session_id,),
            ).fetchall()

        return [
            GridLevel(
                index=row["level_index"],
                price=Decimal(row["price"]),
                status=GridLevelStatus(row["status"]),
            )
            for row in rows
        ]
