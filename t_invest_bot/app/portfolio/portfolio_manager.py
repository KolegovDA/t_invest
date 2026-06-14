from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP

from broker.virtual_broker import VirtualBroker


@dataclass(slots=True)
class PortfolioManager:
    broker: VirtualBroker
    last_prices: dict[str, Decimal] = field(default_factory=dict)

    @property
    def cash(self) -> Decimal:
        return self.broker.cash

    @property
    def realized_profit(self) -> Decimal:
        return self.broker.realized_profit

    def update_price(self, instrument_id: str, price: Decimal) -> None:
        self.last_prices[instrument_id] = price

    def money(self, value: Decimal) -> Decimal:
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def get_market_value(self) -> Decimal:
        market_value = Decimal("0")

        for instrument_id, position in self.broker.positions.items():
            last_price = self.last_prices.get(instrument_id)

            if last_price is None:
                continue

            market_value += last_price * position.quantity

        return market_value

    def get_unrealized_profit(self) -> Decimal:
        unrealized_profit = Decimal("0")

        for instrument_id, position in self.broker.positions.items():
            last_price = self.last_prices.get(instrument_id)

            if last_price is None:
                continue

            unrealized_profit += (
                last_price - position.avg_price
            ) * position.quantity

        return unrealized_profit

    def get_equity(self) -> Decimal:
        return self.cash + self.get_market_value()

    def get_total_profit(self) -> Decimal:
        return self.realized_profit + self.get_unrealized_profit()

    def summary(self) -> None:
        market_value = self.get_market_value()
        equity = self.get_equity()
        unrealized_profit = self.get_unrealized_profit()
        total_profit = self.get_total_profit()

        print("----- PORTFOLIO MANAGER -----")
        print(f"Cash: {self.money(self.cash)}")
        print(f"Market value: {self.money(market_value)}")
        print(f"Equity: {self.money(equity)}")
        print(f"Realized profit: {self.money(self.realized_profit)}")
        print(f"Unrealized profit: {self.money(unrealized_profit)}")
        print(f"Total profit: {self.money(total_profit)}")
        print("Positions:")

        for instrument_id, position in self.broker.positions.items():
            last_price = self.last_prices.get(instrument_id)

            print(
                f"{instrument_id}: "
                f"quantity={position.quantity}, "
                f"avg_price={self.money(position.avg_price)}, "
                f"last_price={last_price}, "
                f"realized_profit={self.money(position.realized_profit)}"
            )

        print("Open level positions:")

        for key, trade in self.broker.level_positions.items():
            instrument_id, level_index = key
            print(
                f"{instrument_id} level={level_index}: "
                f"{trade.quantity} шт. по {self.money(trade.price)}"
            )
