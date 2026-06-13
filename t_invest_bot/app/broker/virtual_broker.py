from dataclasses import dataclass, field
from decimal import Decimal
from typing import List

from domain.commands import PlaceBuyLimitCommand, PlaceSellLimitCommand, TradingCommand
from domain.events import TradeExecutedEvent


@dataclass
class VirtualTrade:
    instrument_id: str
    level_index: int
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

    level_positions: dict[int, VirtualTrade] = field(default_factory=dict)

    def execute_commands(
        self,
        commands: list[TradingCommand],
        current_price: Decimal,
    ) -> list[TradeExecutedEvent]:
        events: list[TradeExecutedEvent] = []

        for command in commands:
            if isinstance(command, PlaceBuyLimitCommand):
                event = self.execute_buy_limit(command, current_price)
                if event:
                    events.append(event)

            elif isinstance(command, PlaceSellLimitCommand):
                event = self.execute_sell_limit(command, current_price)
                if event:
                    events.append(event)

        return events

    def execute_buy_limit(
        self,
        command: PlaceBuyLimitCommand,
        current_price: Decimal,
    ) -> TradeExecutedEvent | None:
        if current_price > command.price:
            return None

        total = command.price * command.quantity

        if self.cash < total:
            print("Недостаточно виртуальных денег")
            return None

        self.cash -= total

        total_position_value = self.avg_price * self.position + total
        self.position += command.quantity
        self.avg_price = total_position_value / self.position

        trade = VirtualTrade(
            instrument_id=command.instrument_id,
            level_index=command.level_index,
            side="BUY",
            quantity=command.quantity,
            price=command.price,
        )

        self.level_positions[command.level_index] = trade
        self.trades.append(trade)

        print(f"BUY level={command.level_index} {command.quantity} {command.instrument_id} по {command.price}")

        return TradeExecutedEvent(
            instrument_id=command.instrument_id,
            level_index=command.level_index,
            side="BUY",
            quantity=command.quantity,
            price=command.price,
        )

    def execute_sell_limit(
        self,
        command: PlaceSellLimitCommand,
        current_price: Decimal,
    ) -> TradeExecutedEvent | None:
        if current_price < command.price:
            return None

        buy_trade = self.level_positions.get(command.level_index)

        if buy_trade is None:
            return None

        if self.position < command.quantity:
            return None

        total = command.price * command.quantity
        profit = (command.price - buy_trade.price) * command.quantity

        self.cash += total
        self.position -= command.quantity
        self.realized_profit += profit

        if self.position == 0:
            self.avg_price = Decimal("0")

        trade = VirtualTrade(
            instrument_id=command.instrument_id,
            level_index=command.level_index,
            side="SELL",
            quantity=command.quantity,
            price=command.price,
            profit=profit,
        )

        self.trades.append(trade)
        del self.level_positions[command.level_index]

        print(f"SELL level={command.level_index} {command.quantity} {command.instrument_id} по {command.price}, profit={profit}")

        return TradeExecutedEvent(
            instrument_id=command.instrument_id,
            level_index=command.level_index,
            side="SELL",
            quantity=command.quantity,
            price=command.price,
        )

    def summary(self) -> None:
        print("----- VIRTUAL BROKER -----")
        print(f"Cash: {self.cash}")
        print(f"Position: {self.position}")
        print(f"Avg price: {self.avg_price}")
        print(f"Realized profit: {self.realized_profit}")
        print(f"Trades: {len(self.trades)}")

        for trade in self.trades:
            print(trade)
