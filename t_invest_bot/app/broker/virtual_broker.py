from dataclasses import dataclass, field
from decimal import Decimal
from typing import List

from domain.commands import PlaceBuyLimitCommand, PlaceSellLimitCommand


@dataclass
class VirtualTrade:
    instrument_id: str
    side: str
    quantity: int
    price: Decimal
    profit: Decimal = Decimal("0")


@dataclass
class VirtualBroker:
    cash: Decimal
    position: int = 0
    avg_price: Decimal = Decimal("0")
    realized_profit: Decimal = Decimal("0")
    trades: List[VirtualTrade] = field(default_factory=list)

    def execute_buy_limit(
        self,
        command: PlaceBuyLimitCommand,
        current_price: Decimal,
    ) -> bool:
        if current_price > command.price:
            return False

        total = command.price * command.quantity

        if self.cash < total:
            print("Недостаточно виртуальных денег")
            return False

        old_position_value = self.avg_price * self.position
        new_position_value = old_position_value + total
        new_position = self.position + command.quantity

        self.cash -= total
        self.position = new_position
        self.avg_price = new_position_value / Decimal(new_position)

        self.trades.append(
            VirtualTrade(
                instrument_id=command.instrument_id,
                side="BUY",
                quantity=command.quantity,
                price=command.price,
            )
        )

        print(f"BUY {command.quantity} {command.instrument_id} по {command.price}")
        return True

    def execute_sell_limit(
        self,
        command: PlaceSellLimitCommand,
        current_price: Decimal,
    ) -> bool:
        if current_price < command.price:
            return False

        if self.position < command.quantity:
            print("Недостаточно позиции для продажи")
            return False

        total = command.price * command.quantity
        profit = (command.price - self.avg_price) * command.quantity

        self.cash += total
        self.position -= command.quantity
        self.realized_profit += profit

        if self.position == 0:
            self.avg_price = Decimal("0")

        self.trades.append(
            VirtualTrade(
                instrument_id=command.instrument_id,
                side="SELL",
                quantity=command.quantity,
                price=command.price,
                profit=profit,
            )
        )

        print(
            f"SELL {command.quantity} {command.instrument_id} "
            f"по {command.price}, profit={profit}"
        )

        return True

    def execute_commands(
        self,
        commands: list,
        current_price: Decimal,
    ) -> None:
        for command in commands:
            if isinstance(command, PlaceBuyLimitCommand):
                self.execute_buy_limit(command, current_price)

            elif isinstance(command, PlaceSellLimitCommand):
                self.execute_sell_limit(command, current_price)

    def summary(self) -> None:
        print("----- VIRTUAL BROKER -----")
        print(f"Cash: {self.cash}")
        print(f"Position: {self.position}")
        print(f"Avg price: {self.avg_price}")
        print(f"Realized profit: {self.realized_profit}")
        print(f"Trades: {len(self.trades)}")

        for trade in self.trades:
            print(trade)
