from dataclasses import dataclass

from application.multi_instrument_sandbox_session import (
    MultiInstrumentSandboxSession,
)
from application.portfolio_manager import PortfolioManager
from application.trade_capital_service import TradeCapitalService
from infrastructure.tinvest.sandbox_account_provider import (
    TInvestSandboxAccountProvider,
)


@dataclass(slots=True)
class MultiInstrumentSessionContext:
    session: MultiInstrumentSandboxSession

    portfolio_manager: PortfolioManager
    trade_capital_service: TradeCapitalService

    sandbox_account_provider: TInvestSandboxAccountProvider
    sandbox_account_id: str

    def close(self) -> None:
        self.session.stop()

        self.sandbox_account_provider.close_account(
            account_id=self.sandbox_account_id,
        )
