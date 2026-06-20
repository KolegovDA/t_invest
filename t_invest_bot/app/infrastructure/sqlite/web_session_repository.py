from dataclasses import dataclass

from infrastructure.sqlite.sqlite_database import SQLiteDatabase
from web.session_registry import WebSession


@dataclass(slots=True)
class SQLiteWebSessionRepository:
    database: SQLiteDatabase

    def save_session(self, session: WebSession) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO web_sessions (
                    ticker,
                    levels,
                    quantity,
                    status,
                    positions,
                    current_price,
                    realized_profit,
                    unrealized_profit
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session.ticker,
                    session.levels,
                    session.quantity,
                    session.status,
                    session.positions,
                    session.current_price,
                    session.realized_profit,
                    session.unrealized_profit,
                ),
            )

    def delete_session(self, ticker: str) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """
                DELETE FROM web_sessions
                WHERE ticker = ?
                """,
                (ticker.upper(),),
            )

    def load_sessions(self) -> list[WebSession]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    ticker,
                    levels,
                    quantity,
                    status,
                    positions,
                    current_price,
                    realized_profit,
                    unrealized_profit
                FROM web_sessions
                ORDER BY ticker
                """
            ).fetchall()

        return [
            WebSession(
                ticker=row["ticker"],
                levels=row["levels"],
                quantity=row["quantity"],
                status=row["status"],
                positions=row["positions"],
                current_price=row["current_price"],
                realized_profit=row["realized_profit"],
                unrealized_profit=row["unrealized_profit"],
            )
            for row in rows
        ]
