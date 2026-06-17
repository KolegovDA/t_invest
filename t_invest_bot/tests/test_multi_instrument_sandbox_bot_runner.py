from decimal import Decimal

from application.multi_instrument_sandbox_bot_runner import (
    MultiInstrumentSandboxBotRunner,
)
from application.portfolio_manager import PortfolioManager
from application.trade_capital_service import TradeCapitalService
from domain.portfolio import Portfolio
from portfolio.capital_reservation_manager import CapitalReservationManager


class FakeMultiInstrumentSession:
    def __init__(self) -> None:
        self.prices = []

    def on_price(
        self,
        instrument_id: str,
        price: Decimal,
    ):
        self.prices.append(
            (instrument_id, price)
        )

        return []

    def poll_executions(self):
        return []


class FakePriceProvider:
    def get_last_price(
        self,
        instrument_uid: str,
    ) -> Decimal:
        if instrument_uid == "SBER_ID":
            return Decimal("300")

        if instrument_uid == "GAZP_ID":
            return Decimal("160")

        return Decimal("0")


def test_multi_instrument_runner_routes_prices_to_all_sessions() -> None:
    session = FakeMultiInstrumentSession()

    runner = MultiInstrumentSandboxBotRunner(
        session=session,
        price_provider=FakePriceProvider(),
        instrument_ids_by_ticker={
            "SBER": "SBER_ID",
            "GAZP": "GAZP_ID",
        },
        tickers_by_instrument_id={
            "SBER_ID": "SBER",
            "GAZP_ID": "GAZP",
        },
        portfolio_manager=PortfolioManager(
            portfolio=Portfolio(
                cash=Decimal("100000"),
            )
        ),
        trade_capital_service=TradeCapitalService(
            portfolio_manager=PortfolioManager(
                portfolio=Portfolio(
                    cash=Decimal("100000"),
                )
            ),
            reservation_manager=CapitalReservationManager(
                available_cash=Decimal("100000"),
            ),
        ),
    )

    runner.run(
        iterations=1,
    )

    assert session.prices == [
        ("SBER_ID", Decimal("300")),
        ("GAZP_ID", Decimal("160")),
    ]
