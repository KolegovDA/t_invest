from dataclasses import dataclass

from application.portfolio_manager import PortfolioManager
from application.trade_capital_service import TradeCapitalService


@dataclass(slots=True)
class SessionReporter:
    portfolio_manager: PortfolioManager
    trade_capital_service: TradeCapitalService

    def print_portfolio(self) -> None:
        portfolio = self.portfolio_manager.portfolio

        print("PORTFOLIO:")
        print("Cash:", portfolio.cash)
        print("Market value:", portfolio.market_value)
        print("Equity:", portfolio.equity)
        print("Realized profit:", portfolio.realized_profit)
        print("Unrealized profit:", portfolio.unrealized_profit)

    def print_capital_reservation(self) -> None:
        reservation_manager = self.trade_capital_service.reservation_manager

        print("CAPITAL RESERVATION:")
        print("Available cash:", reservation_manager.available_cash)
        print("Reserved total:", reservation_manager.get_reserved_total())

    def print_all(self) -> None:
        self.print_portfolio()
        self.print_capital_reservation()
