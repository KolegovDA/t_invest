from dataclasses import dataclass

from application.recovered_session_state import (
    RecoveredSessionState,
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


@dataclass(slots=True)
class RecoveryManager:
    session_repository: SQLiteSessionRepository
    position_repository: SQLitePositionRepository
    portfolio_repository: SQLitePortfolioRepository
    reservation_repository: SQLiteReservationRepository

    def recover(
        self,
        session_id: str,
        available_cash,
    ) -> RecoveredSessionState:
        session = self.session_repository.load_session(
            session_id=session_id,
        )

        return RecoveredSessionState(
            session_id=session["id"],
            account_id=session["account_id"],
            ticker=session["ticker"],
            instrument_id=session["instrument_id"],
            status=session["status"],
            levels=self.session_repository.load_levels(
                session_id,
            ),
            positions=self.position_repository.load_positions(
                session_id,
            ),
            portfolio=self.portfolio_repository.load_portfolio(
                cash=available_cash,
            ),
            reservation_manager=self.reservation_repository.load_reservations(
                available_cash=available_cash,
            ),
        )
