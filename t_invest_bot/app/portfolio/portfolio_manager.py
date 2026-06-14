from dataclasses import dataclass
from decimal import Decimal

from broker.virtual_broker import VirtualBroker
from domain.level_position import LevelPosition


@dataclass
class PortfolioManager:
    broker: VirtualBroker

    def get_cash(self) -> Decimal:
        return self.broker.cash

    def get_total_position(self) -> int:
        return self.broker.position

    def get_realized_profit(self) -> Decimal:
        return self.broker.realized_profit

    def get_level_positions(self) -> dict[int, LevelPosition]:
        return self.broker.level_positions

    def has_open_position(self, level_index: int) -> bool:
        return level_index in self.broker.level_positions

    def print_portfolio(self) -> None:
        print("----- PORTFOLIO -----")
        print(f"Cash: {self.get_cash()}")
        print(f"Total position: {self.get_total_position()}")
        print(f"Realized profit: {self.get_realized_profit()}")
        print("Open level positions:")

        for level_index, position in self.get_level_positions().items():
            print(level_index, position)
