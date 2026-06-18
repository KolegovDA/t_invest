from decimal import Decimal
from pathlib import Path

from application.recovery_manager import RecoveryManager
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


def test_recovery_manager_recovers_saved_session_state(
    tmp_path: Path,
) -> None:
    database = SQLiteDatabase(
        database_path=tmp_path / "test.db",
    )
    database.initialize()

    session_repository = SQLiteSessionRepository(
        database=database,
    )
    position_repository = SQLitePositionRepository(
        database=database,
    )
    portfolio_repository = SQLitePortfolioRepository(
        database=database,
    )
    reservation_repository = SQLiteReservationRepository(
        database=database,
    )

    persistence_service = StatePersistenceService(
        session_repository=session_repository,
        position_repository=position_repository,
        portfolio_repository=portfolio_repository,
        reservation_repository=reservation_repository,
    )

    portfolio = Portfolio(
        cash=Decimal("100000"),
        instruments={
            "SBER_ID": InstrumentPortfolio(
                instrument_id="SBER_ID",
                position_quantity=10,
                average_price=Decimal("300"),
                realized_profit=Decimal("100"),
                buy_commission_total=Decimal("9"),
                last_price=Decimal("310"),
            )
        },
    )

    reservation_manager = CapitalReservationManager(
        available_cash=Decimal("100000"),
    )

    reservation_manager.reserve(
        instrument_id="SBER_ID",
        level_index=1,
        amount=Decimal("300"),
    )

    persistence_service.save_session_state(
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
            )
        ],
        positions={
            1: OpenLevelPosition(
                level_index=1,
                entry_price=Decimal("300"),
                quantity=10,
                buy_commission=Decimal("9"),
                expected_sell_commission_percent=Decimal("0.30"),
                hard_take_profit_price=Decimal("310"),
            )
        },
        portfolio=portfolio,
        reservation_manager=reservation_manager,
    )

    recovery_manager = RecoveryManager(
        session_repository=session_repository,
        position_repository=position_repository,
        portfolio_repository=portfolio_repository,
        reservation_repository=reservation_repository,
    )

    recovered = recovery_manager.recover(
        session_id="session-1",
        available_cash=Decimal("100000"),
    )

    assert recovered.session_id == "session-1"
    assert recovered.account_id == "account-1"
    assert recovered.ticker == "SBER"
    assert recovered.instrument_id == "SBER_ID"
    assert recovered.status == "ACTIVE"

    assert len(recovered.levels) == 1
    assert recovered.levels[0].price == Decimal("300")

    assert len(recovered.positions) == 1
    assert recovered.positions[1].entry_price == Decimal("300")

    assert recovered.portfolio.instruments["SBER_ID"].position_quantity == 10
    assert recovered.reservation_manager.get_reserved_total() == Decimal("300")

def test_recovery_manager_recovers_all_sessions(
    tmp_path: Path,
) -> None:
    database = SQLiteDatabase(
        database_path=tmp_path / "test.db",
    )
    database.initialize()

    session_repository = SQLiteSessionRepository(
        database=database,
    )
    position_repository = SQLitePositionRepository(
        database=database,
    )
    portfolio_repository = SQLitePortfolioRepository(
        database=database,
    )
    reservation_repository = SQLiteReservationRepository(
        database=database,
    )

    persistence_service = StatePersistenceService(
        session_repository=session_repository,
        position_repository=position_repository,
        portfolio_repository=portfolio_repository,
        reservation_repository=reservation_repository,
    )

    portfolio = Portfolio(
        cash=Decimal("100000"),
    )

    reservation_manager = CapitalReservationManager(
        available_cash=Decimal("100000"),
    )

    for session_id, ticker, instrument_id in [
        (
            "session-sber",
            "SBER",
            "SBER_ID",
        ),
        (
            "session-gazp",
            "GAZP",
            "GAZP_ID",
        ),
    ]:
        persistence_service.save_session_state(
            session_id=session_id,
            account_id="account-1",
            ticker=ticker,
            instrument_id=instrument_id,
            status="ACTIVE",
            levels=[
                GridLevel(
                    index=1,
                    price=Decimal("300"),
                    status=GridLevelStatus.WAITING_PRICE,
                )
            ],
            positions={},
            portfolio=portfolio,
            reservation_manager=reservation_manager,
        )

    recovery_manager = RecoveryManager(
        session_repository=session_repository,
        position_repository=position_repository,
        portfolio_repository=portfolio_repository,
        reservation_repository=reservation_repository,
    )

    recovered_sessions = recovery_manager.recover_all(
        available_cash=Decimal("100000"),
    )

    assert len(recovered_sessions) == 2

    tickers = {
        session.ticker
        for session in recovered_sessions
    }

    assert tickers == {
        "SBER",
        "GAZP",
    }
