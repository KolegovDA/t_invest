from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(slots=True)
class InstrumentPortfolio:
    instrument_id: str

    position_quantity: int = 0
    average_price: Decimal = Decimal("0")

    buy_commission_total: Decimal = Decimal("0")
    realized_profit: Decimal = Decimal("0")

    reserved_capital: Decimal = Decimal("0")
    last_price: Decimal = Decimal("0")

    @property
    def market_value(self) -> Decimal:
        return self.last_price * self.position_quantity

    @property
    def unrealized_profit(self) -> Decimal:
        if self.position_quantity == 0:
            return Decimal("0")

        return (
            self.last_price
            - self.average_price
        ) * self.position_quantity


@dataclass(slots=True)
class Portfolio:
    cash: Decimal = Decimal("0")

    instruments: dict[str, InstrumentPortfolio] = field(
        default_factory=dict
    )

    @property
    def realized_profit(self) -> Decimal:
        return sum(
            (
                instrument.realized_profit
                for instrument in self.instruments.values()
            ),
            start=Decimal("0"),
        )

    @property
    def unrealized_profit(self) -> Decimal:
        return sum(
            (
                instrument.unrealized_profit
                for instrument in self.instruments.values()
            ),
            start=Decimal("0"),
        )

    @property
    def market_value(self) -> Decimal:
        return sum(
            (
                instrument.market_value
                for instrument in self.instruments.values()
            ),
            start=Decimal("0"),
        )

    @property
    def equity(self) -> Decimal:
        return self.cash + self.market_value
