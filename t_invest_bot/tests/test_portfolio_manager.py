from decimal import Decimal

from application.portfolio_manager import (
    PortfolioManager,
)
from domain.portfolio import Portfolio


def test_portfolio_manager_tracks_position_and_profit() -> None:
    manager = PortfolioManager(
        portfolio=Portfolio(
            cash=Decimal("100000"),
        )
    )

    manager.on_buy(
        instrument_id="SBER",
        quantity=10,
        price=Decimal("300"),
    )

    manager.update_market_price(
        instrument_id="SBER",
        price=Decimal("310"),
    )

    instrument = (
        manager.portfolio.instruments[
            "SBER"
        ]
    )

    assert instrument.position_quantity == 10
    assert instrument.average_price == Decimal("300")

    assert instrument.market_value == Decimal(
        "3100"
    )

    assert instrument.unrealized_profit == Decimal(
        "100"
    )

    manager.on_sell(
        instrument_id="SBER",
        quantity=10,
        price=Decimal("310"),
        profit=Decimal("100"),
    )

    assert (
        instrument.position_quantity
        == 0
    )

    assert (
        instrument.realized_profit
        == Decimal("100")
    )

    assert (
        manager.portfolio.realized_profit
        == Decimal("100")
    )
