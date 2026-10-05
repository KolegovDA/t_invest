from dataclasses import dataclass

from infrastructure.sqlite.sqlite_database import (
    SQLiteDatabase,
)


@dataclass(slots=True)
class SQLiteAccountBackfillRepository:
    database: SQLiteDatabase

    def is_done(
        self,
        trading_account_id: str,
    ) -> bool:
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT trading_account_id
                FROM account_backfills
                WHERE trading_account_id = ?
                """,
                (
                    trading_account_id,
                ),
            ).fetchone()

        return row is not None

    def mark_done(
        self,
        trading_account_id: str,
        created_at: str,
    ) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO account_backfills (
                    trading_account_id,
                    created_at
                )
                VALUES (?, ?)
                """,
                (
                    trading_account_id,
                    created_at,
                ),
            )
