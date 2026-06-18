from decimal import Decimal
from pathlib import Path

from infrastructure.sqlite.reservation_repository import (
    SQLiteReservationRepository,
)
from infrastructure.sqlite.sqlite_database import SQLiteDatabase
from portfolio.capital_reservation_manager import CapitalReservationManager


def test_sqlite_reservation_repository_saves_and_loads_reservations(
    tmp_path: Path,
) -> None:
    database = SQLiteDatabase(
        database_path=tmp_path / "test.db",
    )

    database.initialize()

    repository = SQLiteReservationRepository(
        database=database,
    )

    manager = CapitalReservationManager(
        available_cash=Decimal("1000"),
    )

    manager.reserve(
        instrument_id="SBER_ID",
        level_index=1,
        amount=Decimal("300"),
    )

    manager.reserve(
        instrument_id="GAZP_ID",
        level_index=2,
        amount=Decimal("100"),
    )

    repository.save_reservations(
        reservation_manager=manager,
    )

    loaded = repository.load_reservations(
        available_cash=Decimal("1000"),
    )

    assert loaded.get_reserved_total() == Decimal("400")
    assert loaded.available_cash == Decimal("600")
