from dataclasses import dataclass
from decimal import Decimal

from broker.virtual_broker import VirtualBroker


@dataclass(slots=True)
class PortfolioManager:
    broker: VirtualBroker

    @property
    def cash(self) -> Decimal:
        return self.broker.cash

    @property
    def realized_profit(self) -> Decimal:
        return self.broker.realized_profit

    def summary(self) -> None:
        print("----- PORTFOLIO MANAGER -----")
        print(f"Cash: {self.cash}")
        print(f"Realized profit: {self.realized_profit}")
        print("Positions:")

        for position in self.broker.positions.values():
            print(
                f"{position.instrument_id}: "
                f"quantity={position.quantity}, "
                f"avg_price={position.avg_price}, "
                f"realized_profit={position.realized_profit}"
            )

        print("Open level positions:")

        for key, trade in self.broker.level_positions.items():
            instrument_id, level_index = key
            print(
                f"{instrument_id} level={level_index}: "
                f"{trade.quantity} шт. по {trade.price}"
            )
