from decimal import Decimal
from dataclasses import dataclass, field
from typing import List

from strategy.grid_engine import PlaceBuyLimitCommand


@dataclass
class VirtualTrade:
    instrument_id: str
    side: str
    quantity: int
    price: Decimal


@dataclass
class VirtualBroker:
    cash: Decimal
    position: int = 0
    trades: List[VirtualTrade] = field(default_factory=list)

    def execute_buy_limit(
        self,
        command: PlaceBuyLimitCommand,
        current_price: Decimal,
    ) -> bool:
        """
        Виртуально исполняем лимитную покупку.

        Buy Limit исполняется, если текущая цена <= цене заявки.
        """

        if current_price > command.price:
            return False

        total = command.price * command.quantity

        if self.cash < total:
            print("Недостаточно виртуальных денег")
            return False

        self.cash -= total
        self.position += command.quantity

        trade = VirtualTrade(
            instrument_id=command.instrument_id,
            side="BUY",
            quantity=command.quantity,
            price=command.price,
        )

        self.trades.append(trade)

        print(f"BUY {command.quantity} {command.instrument_id} по {command.price}")

        return True

    def execute_commands(
        self,
        commands: list,
        current_price: Decimal,
    ) -> None:
        for command in commands:
            if isinstance(command, PlaceBuyLimitCommand):
                self.execute_buy_limit(command, current_price)

    def summary(self) -> None:
        print("----- VIRTUAL BROKER -----")
        print(f"Cash: {self.cash}")
        print(f"Position: {self.position}")
        print(f"Trades: {len(self.trades)}")

        for trade in self.trades:
            print(trade)
