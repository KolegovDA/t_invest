from decimal import Decimal
from pathlib import Path

from application.state_persistence_service import (
    StatePersistenceService,
)
from domain.portfolio import (
    InstrumentPortfolio,
    Portfolio,
)
from infrastructure.sqlite.portfolio_repository import (
    SQLitePortfolioRepository,
)
from infrastructure.sqlite.position_repository import (
    SQLitePositionRepository,
)
from infrastructure.sqlite.reservation_repository import (
    SQLiteReservationRepository,
)
from infrastructure.sqlite.session_repository import (
    SQLiteSessionRepository,
)
from infrastructure.sqlite.sqlite_database import (
    SQLiteDatabase,
)
from portfolio.capital_reservation_manager import (
    CapitalReservationManager,
)
from strategy.grid_engine import (
    GridLevel,
    GridLevelStatus,
    OpenLevelPosition,
)


def test_state_persistence_service_saves_all_parts(
    tmp_path: Path,
) -> None:
    database = SQLiteDatabase(
        database_path=tmp_path / "test.db",
    )

    database.initialize()

    service = StatePersistenceService(
        session_repository=SQLiteSessionRepository(
            database=database,
        ),
        position_repository=SQLitePositionRepository(
            database=database,
        ),
        portfolio_repository=SQLitePortfolioRepository(
            database=database,
        ),
        reservation_repository=SQLiteReservationRepository(
            database=database,
        ),
    )

    portfolio = Portfolio(
        cash=Decimal("100000"),
        instruments={
            "SBER": InstrumentPortfolio(
                instrument_id="SBER",
                position_quantity=10,
                average_price=Decimal("300"),
                realized_profit=Decimal("0"),
                buy_commission_total=Decimal("9"),
                last_price=Decimal("310"),
            ),
        },
    )

    reservations = CapitalReservationManager(
        available_cash=Decimal("100000"),
    )

    reservations.reserve(
        instrument_id="SBER",
        level_index=1,
        amount=Decimal("300"),
    )

    service.save_session_state(
        session_id="session-1",
        account_id="account-1",
        ticker="SBER",
        instrument_id="SBER_ID",
        status="ACTIVE",
        levels=[
            GridLevel(
                index=1,
                price=Decimal("300"),
                status=GridLevelStatus.WAITING_PRICE,
            ),
        ],
        positions={
            1: OpenLevelPosition(
                level_index=1,
                entry_price=Decimal("300"),
                quantity=10,
                buy_commission=Decimal("9"),
                expected_sell_commission_percent=Decimal("0.30"),
                hard_take_profit_price=Decimal("310"),
            ),
        },
        portfolio=portfolio,
        reservation_manager=reservations,
    )

    levels = service.session_repository.load_levels(
        "session-1",
    )

    positions = service.position_repository.load_positions(
        "session-1",
    )

    assert len(levels) == 1
    assert len(positions) == 1
