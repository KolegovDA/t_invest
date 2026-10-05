from dataclasses import dataclass
from decimal import Decimal

from domain.money_movement import (
    MoneyMovement,
)
from infrastructure.sqlite.sqlite_database import (
    SQLiteDatabase,
)


@dataclass(slots=True)
class SQLiteMoneyMovementRepository:
    database: SQLiteDatabase

    def record(
        self,
        movement: MoneyMovement,
    ) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO money_movements (
                    created_at,
                    trading_account_id,
                    amount,
                    note
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    movement.created_at,
                    movement.trading_account_id,
                    str(
                        movement.amount
                    ),
                    movement.note,
                ),
            )

    def get_since(
        self,
        since: str,
    ) -> (
        list[MoneyMovement]
    ):
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    id,
                    created_at,
                    trading_account_id,
                    amount,
                    note
                FROM money_movements
                WHERE created_at >= ?
                ORDER BY id ASC
                """,
                (
                    since,
                ),
            ).fetchall()

        return [
            MoneyMovement(
                id=int(
                    row[
                        "id"
                    ]
                ),

                created_at=(
                    row[
                        "created_at"
                    ]
                ),

                trading_account_id=(
                    row[
                        "trading_account_id"
                    ]
                ),

                amount=Decimal(
                    row[
                        "amount"
                    ]
                ),

                note=(
                    row[
                        "note"
                    ]
                ),
            )

            for row in rows
        ]

    def get_by_account(
        self,
        trading_account_id: str,
    ) -> (
        list[MoneyMovement]
    ):
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    id,
                    created_at,
                    trading_account_id,
                    amount,
                    note
                FROM money_movements
                WHERE trading_account_id = ?
                ORDER BY id DESC
                """,
                (
                    trading_account_id,
                ),
            ).fetchall()

        return [
            MoneyMovement(
                id=int(
                    row[
                        "id"
                    ]
                ),

                created_at=(
                    row[
                        "created_at"
                    ]
                ),

                trading_account_id=(
                    row[
                        "trading_account_id"
                    ]
                ),

                amount=Decimal(
                    row[
                        "amount"
                    ]
                ),

                note=(
                    row[
                        "note"
                    ]
                ),
            )

            for row in rows
        ]
