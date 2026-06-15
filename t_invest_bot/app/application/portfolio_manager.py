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
        quantity: int,
        price: Decimal,
        commission: Decimal = Decimal("0"),
    ) -> None:
        instrument = self.get_or_create(
            instrument_id,
        )

        buy_amount = (
            price * quantity
            + commission
        )

        self.portfolio.cash -= buy_amount

        old_quantity = instrument.position_quantity

        new_quantity = (
            old_quantity
            + quantity
        )

        if old_quantity == 0:
            instrument.average_price = price
        else:
            instrument.average_price = (
                (
                    instrument.average_price
                    * old_quantity
                )
                + (price * quantity)
            ) / new_quantity

        instrument.position_quantity = new_quantity

    def on_sell(
        self,
        instrument_id: str,
        quantity: int,
        price: Decimal,
        profit: Decimal,
        commission: Decimal = Decimal("0"),
    ) -> None:
        instrument = self.get_or_create(
            instrument_id,
        )

        sell_amount = (
            price * quantity
            - commission
        )

        self.portfolio.cash += sell_amount

        instrument.position_quantity -= quantity

        instrument.realized_profit += profit

        if instrument.position_quantity == 0:
            instrument.average_price = Decimal("0")
