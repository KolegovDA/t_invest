from dataclasses import dataclass
from typing import Any

from portfolio.capital_reservation_manager import (
    CapitalReservationManager,
)


@dataclass(slots=True)
class AccountContext:
    account_id: str
    portfolio_manager: Any
    reservation_manager: CapitalReservationManager
    sessions: dict[str, Any]
