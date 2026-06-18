from dataclasses import dataclass
from decimal import Decimal

from infrastructure.sqlite.sqlite_database import SQLiteDatabase
from strategy.grid_engine import OpenLevelPosition


@dataclass(slots=True)
class SQLitePositionRepository:
    database: SQLiteDatabase

    def save_positions(
        self,
        session_id: str,
        positions: dict[int, OpenLevelPosition],
    ) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """
                DELETE FROM positions
                WHERE session_id = ?
                """,
                (session_id,),
            )

            connection.executemany(
                """
                INSERT INTO positions (
                    session_id,
                    level_index,
                    quantity,
                    entry_price,
                    buy_commission,
                    expected_sell_commission_percent,
                    hard_take_profit_price
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        session_id,
                        position.level_index,
                        position.quantity,
                        str(position.entry_price),
                        str(position.buy_commission),
                        str(position.expected_sell_commission_percent),
                        str(position.hard_take_profit_price),
                    )
                    for position in positions.values()
                ],
            )

    def load_positions(
        self,
        session_id: str,
    ) -> dict[int, OpenLevelPosition]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    level_index,
                    quantity,
                    entry_price,
                    buy_commission,
                    expected_sell_commission_percent,
                    hard_take_profit_price
                FROM positions
                WHERE session_id = ?
                ORDER BY level_index
                """,
                (session_id,),
            ).fetchall()

        result: dict[int, OpenLevelPosition] = {}

        for row in rows:
            position = OpenLevelPosition(
                level_index=row["level_index"],
                entry_price=Decimal(row["entry_price"]),
                quantity=row["quantity"],
                buy_commission=Decimal(row["buy_commission"]),
                expected_sell_commission_percent=Decimal(
                    row["expected_sell_commission_percent"]
                ),
                hard_take_profit_price=Decimal(
                    row["hard_take_profit_price"]
                ),
            )

            result[position.level_index] = position

        return result
