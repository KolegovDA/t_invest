from dataclasses import dataclass

from domain.portfolio import Portfolio
from portfolio.capital_reservation_manager import (
    CapitalReservationManager,
)
from strategy.grid_engine import (
    GridLevel,
    OpenLevelPosition,
)


@dataclass(slots=True)
class RecoveredSessionState:
    session_id: str
    account_id: str
    ticker: str
    instrument_id: str
    status: str

    levels: list[GridLevel]

    positions: dict[int, OpenLevelPosition]

    portfolio: Portfolio

    reservation_manager: CapitalReservationManager
