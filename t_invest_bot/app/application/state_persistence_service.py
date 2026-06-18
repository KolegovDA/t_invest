from dataclasses import dataclass
from datetime import datetime, timezone

from domain.portfolio import Portfolio
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
from portfolio.capital_reservation_manager import (
    CapitalReservationManager,
)
from strategy.grid_engine import (
    GridLevel,
    OpenLevelPosition,
)


@dataclass(slots=True)
class StatePersistenceService:
    session_repository: SQLiteSessionRepository
    position_repository: SQLitePositionRepository
    portfolio_repository: SQLitePortfolioRepository
    reservation_repository: SQLiteReservationRepository

    def save_session_state(
        self,
        session_id: str,
        account_id: str,
        ticker: str,
        instrument_id: str,
        status: str,
        levels: list[GridLevel],
        positions: dict[int, OpenLevelPosition],
        portfolio: Portfolio,
        reservation_manager: CapitalReservationManager,
    ) -> None:
        self.session_repository.save_session(
            session_id=session_id,
            account_id=account_id,
            ticker=ticker,
            instrument_id=instrument_id,
            status=status,
            created_at=datetime.now(timezone.utc),
            levels=levels,
        )

        self.position_repository.save_positions(
            session_id=session_id,
            positions=positions,
        )

        self.portfolio_repository.save_portfolio(
            portfolio=portfolio,
        )

        self.reservation_repository.save_reservations(
            reservation_manager=reservation_manager,
        )
