from dataclasses import dataclass
from decimal import Decimal

from application.portfolio_manager import PortfolioManager
from portfolio.capital_reservation_manager import CapitalReservationManager


@dataclass(slots=True)
class TradeCapitalService:
    portfolio_manager: PortfolioManager
    reservation_manager: CapitalReservationManager

    def reserve_for_buy(
        self,
        instrument_id: str,
        level_index: int,
        quantity: int,
        price: Decimal,
        commission_percent: Decimal,
    ) -> bool:
        amount = self.calculate_required_buy_amount(
            quantity=quantity,
            price=price,
            commission_percent=commission_percent,
        )

        result = self.reservation_manager.reserve(
            instrument_id=instrument_id,
            level_index=level_index,
            amount=amount,
        )

        return result.success

    def release_after_buy_execution(
        self,
        instrument_id: str,
        level_index: int,
    ) -> Decimal:
        return self.reservation_manager.release(
            instrument_id=instrument_id,
            level_index=level_index,
        )

    def calculate_required_buy_amount(
        self,
        quantity: int,
        price: Decimal,
        commission_percent: Decimal,
    ) -> Decimal:
        gross = price * quantity
        commission = gross * commission_percent / Decimal("100")

        return gross + commission
