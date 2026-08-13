from dataclasses import dataclass
from decimal import Decimal

from application.multi_instrument_sandbox_session import (
    MultiInstrumentSandboxSession,
)
from application.portfolio_manager import PortfolioManager
from application.trade_capital_service import TradeCapitalService
from infrastructure.tinvest.last_price_provider import (
    TInvestLastPriceProvider,
)
from infrastructure.tinvest.sandbox_account_provider import (
    TInvestSandboxAccountProvider,
)


@dataclass(slots=True)
class MultiInstrumentSessionContext:
    session: MultiInstrumentSandboxSession

    portfolio_manager: PortfolioManager
    trade_capital_service: TradeCapitalService
    price_provider: TInvestLastPriceProvider

    sandbox_account_provider: (
        TInvestSandboxAccountProvider | None
    )
    sandbox_account_id: str
    sandbox_balance: Decimal

    instrument_ids_by_ticker: dict[str, str]
    tickers_by_instrument_id: dict[str, str]

    is_live: bool = False
    close_account_on_close: bool = False

    @property
    def account_id(self) -> str:
        return self.sandbox_account_id

    @property
    def balance(self) -> Decimal:
        return self.sandbox_balance

    @property
    def mode(self) -> str:
        return (
            "live"
            if self.is_live
            else "sandbox"
        )

    def close(self) -> None:
        self.session.stop()

        if (
            self.sandbox_account_provider
            is not None
            and self.close_account_on_close
        ):
            self.sandbox_account_provider.close_account(
                account_id=self.sandbox_account_id,
            )
