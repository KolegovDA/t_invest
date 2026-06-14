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

        print("Open level positions:")
        for position in self.broker.level_positions.values():
            print(
                f"{position.instrument_id} level={position.level_index}: "
                f"quantity={position.quantity}, "
                f"entry_price={position.entry_price}"
            )
