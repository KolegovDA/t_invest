from decimal import Decimal
from pathlib import Path

from infrastructure.sqlite.position_repository import (
    SQLitePositionRepository,
)
from infrastructure.sqlite.sqlite_database import SQLiteDatabase
from strategy.grid_engine import OpenLevelPosition


def test_sqlite_position_repository_saves_and_loads_positions(
    tmp_path: Path,
) -> None:
    database = SQLiteDatabase(
        database_path=tmp_path / "test.db",
    )

    database.initialize()

    repository = SQLitePositionRepository(
        database=database,
    )

    repository.save_positions(
        session_id="session-1",
        positions={
            1: OpenLevelPosition(
                level_index=1,
                entry_price=Decimal("300"),
                quantity=10,
                buy_commission=Decimal("9"),
                expected_sell_commission_percent=Decimal("0.30"),
                hard_take_profit_price=Decimal("310"),
            ),
            2: OpenLevelPosition(
                level_index=2,
                entry_price=Decimal("290"),
                quantity=20,
                buy_commission=Decimal("17.4"),
                expected_sell_commission_percent=Decimal("0.30"),
                hard_take_profit_price=Decimal("300"),
            ),
        },
    )

    positions = repository.load_positions(
        session_id="session-1",
    )

    assert len(positions) == 2

    assert positions[1].entry_price == Decimal("300")
    assert positions[1].quantity == 10
    assert positions[1].buy_commission == Decimal("9")
    assert positions[1].expected_sell_commission_percent == Decimal("0.30")
    assert positions[1].hard_take_profit_price == Decimal("310")

    assert positions[2].entry_price == Decimal("290")
    assert positions[2].quantity == 20
    assert positions[2].buy_commission == Decimal("17.4")
    assert positions[2].expected_sell_commission_percent == Decimal("0.30")
    assert positions[2].hard_take_profit_price == Decimal("300")
