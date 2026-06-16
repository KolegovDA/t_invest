from dataclasses import dataclass

from application.multi_instrument_sandbox_session import (
    MultiInstrumentSandboxSession,
)
from application.portfolio_manager import PortfolioManager
from application.trade_capital_service import TradeCapitalService


@dataclass(slots=True)
class MultiInstrumentSessionContext:
    session: MultiInstrumentSandboxSession

    portfolio_manager: PortfolioManager
    trade_capital_service: TradeCapitalService

    sandbox_account_id: str

    def close(self) -> None:
        self.session.stop()
