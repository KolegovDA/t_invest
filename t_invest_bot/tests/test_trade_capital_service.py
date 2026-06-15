from decimal import Decimal

from application.portfolio_manager import PortfolioManager
from application.trade_capital_service import TradeCapitalService
from domain.portfolio import Portfolio
from portfolio.capital_reservation_manager import CapitalReservationManager


def test_trade_capital_service_reserves_buy_amount_with_commission() -> None:
    reservation_manager = CapitalReservationManager(
        available_cash=Decimal("1000"),
    )

    service = TradeCapitalService(
        portfolio_manager=PortfolioManager(
            portfolio=Portfolio(
                cash=Decimal("1000"),
            )
        ),
        reservation_manager=reservation_manager,
    )

    success = service.reserve_for_buy(
        instrument_id="SBER",
        level_index=1,
        quantity=1,
        price=Decimal("300"),
        commission_percent=Decimal("0.30"),
    )

    assert success is True
    assert reservation_manager.available_cash == Decimal("699.10")
    assert reservation_manager.get_reserved_total() == Decimal("300.90")


def test_trade_capital_service_fails_when_cash_is_not_enough() -> None:
    reservation_manager = CapitalReservationManager(
        available_cash=Decimal("100"),
    )

    service = TradeCapitalService(
        portfolio_manager=PortfolioManager(
            portfolio=Portfolio(
                cash=Decimal("100"),
            )
        ),
        reservation_manager=reservation_manager,
    )

    success = service.reserve_for_buy(
        instrument_id="SBER",
        level_index=1,
        quantity=1,
        price=Decimal("300"),
        commission_percent=Decimal("0.30"),
    )

    assert success is False
    assert reservation_manager.available_cash == Decimal("100")
    assert reservation_manager.get_reserved_total() == Decimal("0")


def test_trade_capital_service_releases_after_buy_execution() -> None:
    reservation_manager = CapitalReservationManager(
        available_cash=Decimal("1000"),
    )

    service = TradeCapitalService(
        portfolio_manager=PortfolioManager(
            portfolio=Portfolio(
                cash=Decimal("1000"),
            )
        ),
        reservation_manager=reservation_manager,
    )

    service.reserve_for_buy(
        instrument_id="SBER",
        level_index=1,
        quantity=1,
        price=Decimal("300"),
        commission_percent=Decimal("0.30"),
    )

    released = service.release_after_buy_execution(
        instrument_id="SBER",
        level_index=1,
    )

    assert released == Decimal("300.90")
    assert reservation_manager.available_cash == Decimal("1000")
    assert reservation_manager.get_reserved_total() == Decimal("0")
