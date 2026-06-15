from decimal import Decimal

from application.portfolio_manager import PortfolioManager
from application.trade_event_handler import TradeEventHandler
from domain.events import TradeExecutedEvent
from domain.portfolio import Portfolio


def test_trade_event_handler_updates_portfolio_on_buy_and_sell() -> None:
    portfolio_manager = PortfolioManager(
        portfolio=Portfolio(
            cash=Decimal("100000"),
        )
    )

    handler = TradeEventHandler(
        portfolio_manager=portfolio_manager,
    )

    handler.handle(
        TradeExecutedEvent(
            instrument_id="SBER",
            level_index=1,
            side="BUY",
            quantity=10,
            price=Decimal("300"),
            commission=None,
        )
    )

    instrument = portfolio_manager.portfolio.instruments["SBER"]

    assert instrument.position_quantity == 10
    assert instrument.average_price == Decimal("300")

    handler.handle(
        TradeExecutedEvent(
            instrument_id="SBER",
            level_index=1,
            side="SELL",
            quantity=10,
            price=Decimal("310"),
            commission=Decimal("9.3"),
        )
    )

    assert instrument.position_quantity == 0
    assert instrument.realized_profit == Decimal("90.7")
    assert portfolio_manager.portfolio.realized_profit == Decimal("90.7")
