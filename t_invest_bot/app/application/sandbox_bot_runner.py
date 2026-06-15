from dataclasses import dataclass
from time import sleep

from application.portfolio_manager import PortfolioManager
from application.sandbox_trading_session import SandboxTradingSession
from application.trade_capital_service import TradeCapitalService
from infrastructure.tinvest.last_price_provider import TInvestLastPriceProvider


@dataclass(slots=True)
class SandboxBotRunner:
    session: SandboxTradingSession
    instrument_id: str
    price_provider: TInvestLastPriceProvider
    portfolio_manager: PortfolioManager | None = None
    trade_capital_service: TradeCapitalService | None = None

    polling_interval_seconds: int = 10

    def run(
        self,
        iterations: int | None = None,
    ) -> None:
        counter = 0

        while True:
            price = self.price_provider.get_last_price(
                instrument_uid=self.instrument_id,
            )

            if self.portfolio_manager is not None:
                self.portfolio_manager.update_market_price(
                    instrument_id=self.instrument_id,
                    price=price,
                )

            placed_orders = self.session.on_price(
                price=price,
            )

            executed_events = self.session.poll_executions()

            print(
                f"PRICE={price} "
                f"PLACED={len(placed_orders)} "
                f"EXECUTED={len(executed_events)}"
            )

            for order in placed_orders:
                print("PLACED ORDER:", order)

            for event in executed_events:
                print("EXECUTED EVENT:", event)

            if self.portfolio_manager is not None:
                self._print_portfolio()

            if self.trade_capital_service is not None:
                self._print_capital_reservation()

            counter += 1

            if (
                iterations is not None
                and counter >= iterations
            ):
                return

            sleep(
                self.polling_interval_seconds
            )

    def _print_portfolio(self) -> None:
        if self.portfolio_manager is None:
            return

        portfolio = self.portfolio_manager.portfolio

        print("PORTFOLIO:")
        print("Cash:", portfolio.cash)
        print("Market value:", portfolio.market_value)
        print("Equity:", portfolio.equity)
        print("Realized profit:", portfolio.realized_profit)
        print("Unrealized profit:", portfolio.unrealized_profit)

    def _print_capital_reservation(self) -> None:
        if self.trade_capital_service is None:
            return

        reservation_manager = self.trade_capital_service.reservation_manager

        print("CAPITAL RESERVATION:")
        print("Available cash:", reservation_manager.available_cash)
        print("Reserved total:", reservation_manager.get_reserved_total())
