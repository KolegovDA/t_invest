from dataclasses import dataclass
from decimal import Decimal

from domain.portfolio import (
    InstrumentPortfolio,
    Portfolio,
)


@dataclass(slots=True)
class PortfolioManager:
    portfolio: Portfolio

    def get_or_create(
        self,
        instrument_id: str,
    ) -> InstrumentPortfolio:
        if instrument_id not in self.portfolio.instruments:
            self.portfolio.instruments[
                instrument_id
            ] = InstrumentPortfolio(
                instrument_id=instrument_id,
            )

        return self.portfolio.instruments[
            instrument_id
        ]

    def update_market_price(
        self,
        instrument_id: str,
        price: Decimal,
    ) -> None:
        instrument = self.get_or_create(
            instrument_id,
        )

        instrument.last_price = price

    def on_buy(
        self,
        instrument_id: str,
        quantity: int | Decimal,
        price: Decimal,
        commission: Decimal = Decimal("0"),
        gross_amount: Decimal | None = None,
    ) -> None:
        instrument = self.get_or_create(
            instrument_id,
        )

        gross_buy = gross_amount if gross_amount is not None else price * quantity
        buy_amount = gross_buy + commission

        self.portfolio.cash -= buy_amount

        old_quantity = instrument.position_quantity
        new_quantity = old_quantity + quantity

        instrument.average_price = (
            instrument.average_price * old_quantity + gross_buy
        ) / new_quantity

        instrument.position_quantity = new_quantity
        instrument.buy_commission_total += commission

    def on_sell(
        self,
        instrument_id: str,
        quantity: int | Decimal,
        price: Decimal,
        profit: Decimal,
        commission: Decimal = Decimal("0"),
        buy_commission_to_close: Decimal = Decimal("0"),
        gross_amount: Decimal | None = None,
        purchase_cost_to_close: Decimal | None = None,
    ) -> None:
        instrument = self.get_or_create(
            instrument_id,
        )

        gross_sell = gross_amount if gross_amount is not None else price * quantity
        sell_amount = gross_sell - commission
        remaining_gross_cost = instrument.average_price * instrument.position_quantity
        if purchase_cost_to_close is not None:
            remaining_gross_cost -= purchase_cost_to_close - buy_commission_to_close

        self.portfolio.cash += sell_amount

        instrument.position_quantity -= quantity
        instrument.realized_profit += profit
        instrument.buy_commission_total -= buy_commission_to_close

        if instrument.position_quantity == 0:
            instrument.average_price = Decimal("0")
            instrument.buy_commission_total = Decimal("0")
        elif purchase_cost_to_close is not None:
            instrument.average_price = remaining_gross_cost / instrument.position_quantity
