from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from infrastructure.sqlite.sqlite_database import SQLiteDatabase
from portfolio.capital_reservation_manager import CapitalReservationManager


@dataclass(slots=True)
class SQLiteReservationRepository:
    database: SQLiteDatabase

    def save_reservations(
        self,
        reservation_manager: CapitalReservationManager,
    ) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """
                DELETE FROM reservations
                """
            )

            connection.executemany(
                """
                INSERT INTO reservations (
                    instrument_id,
                    level_index,
                    amount
                )
                VALUES (?, ?, ?)
                """,
                [
                    (
                        instrument_id,
                        level_index,
                        str(self._extract_amount(value)),
                    )
                    for (
                        instrument_id,
                        level_index,
                    ), value in reservation_manager.reservations.items()
                ],
            )

    def load_reservations(
        self,
        available_cash: Decimal,
    ) -> CapitalReservationManager:
        manager = CapitalReservationManager(
            available_cash=available_cash,
        )

        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    instrument_id,
                    level_index,
                    amount
                FROM reservations
                """
            ).fetchall()

        for row in rows:
            manager.reserve(
                instrument_id=row["instrument_id"],
                level_index=row["level_index"],
                amount=Decimal(str(row["amount"])),
            )

        return manager

    def _extract_amount(
        self,
        value: Any,
    ) -> Decimal:
        if isinstance(value, Decimal):
            return value

        if hasattr(value, "amount"):
            return Decimal(str(value.amount))

        if hasattr(value, "reserved_amount"):
            return Decimal(str(value.reserved_amount))

        return Decimal(str(value))
