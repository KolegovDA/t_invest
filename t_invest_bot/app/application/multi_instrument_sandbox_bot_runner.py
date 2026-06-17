from dataclasses import dataclass
from time import sleep

from application.multi_instrument_sandbox_session import (
    MultiInstrumentSandboxSession,
)
from application.portfolio_manager import PortfolioManager
from application.session_reporter import SessionReporter
from application.trade_capital_service import TradeCapitalService
from infrastructure.tinvest.last_price_provider import (
    TInvestLastPriceProvider,
)


@dataclass(slots=True)
class MultiInstrumentSandboxBotRunner:
    session: MultiInstrumentSandboxSession
    price_provider: TInvestLastPriceProvider
    instrument_ids_by_ticker: dict[str, str]
    tickers_by_instrument_id: dict[str, str]
    portfolio_manager: PortfolioManager
    trade_capital_service: TradeCapitalService

    polling_interval_seconds: int = 10

    def run(
        self,
        iterations: int | None = None,
    ) -> None:
        reporter = SessionReporter(
            portfolio_manager=self.portfolio_manager,
            trade_capital_service=self.trade_capital_service,
        )

        counter = 0

        while True:
            for ticker, instrument_id in self.instrument_ids_by_ticker.items():
                price = self.price_provider.get_last_price(
                    instrument_uid=instrument_id,
                )

                self.portfolio_manager.update_market_price(
                    instrument_id=instrument_id,
                    price=price,
                )

                placed_orders = self.session.on_price(
                    instrument_id=instrument_id,
                    price=price,
                )

                print(
                    f"{ticker} PRICE={price} "
                    f"PLACED={len(placed_orders)}"
                )

                for order in placed_orders:
                    print(f"{ticker} PLACED ORDER:", order)

            executed_events = self.session.poll_executions()

            print(
                "EXECUTED:",
                len(executed_events),
            )

            for event in executed_events:
                ticker = self.tickers_by_instrument_id.get(
                    event.instrument_id,
                    event.instrument_id,
                )

                print(
                    f"{ticker} EXECUTED EVENT:",
                    event,
                )

            reporter.print_all()

            counter += 1

            if (
                iterations is not None
                and counter >= iterations
            ):
                return

            sleep(
                self.polling_interval_seconds,
            )
