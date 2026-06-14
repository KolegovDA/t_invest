from dataclasses import dataclass, field
from decimal import Decimal
from typing import List

from domain.commands import PlaceBuyLimitCommand, PlaceSellLimitCommand, TradingCommand
from domain.events import TradeExecutedEvent
from domain.position import Position


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
    positions: dict[str, Position] = field(default_factory=dict)
    realized_profit: Decimal = Decimal("0")
    trades: List[VirtualTrade] = field(default_factory=list)
    level_positions: dict[tuple[str, int], VirtualTrade] = field(default_factory=dict)

    def get_position(self, instrument_id: str) -> Position:
        if instrument_id not in self.positions:
            self.positions[instrument_id] = Position(instrument_id=instrument_id)
        return self.positions[instrument_id]

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

        position = self.get_position(command.instrument_id)

        self.cash -= total

        total_position_value = position.avg_price * position.quantity + total
        position.quantity += command.quantity
        position.avg_price = total_position_value / position.quantity

        trade = VirtualTrade(
            instrument_id=command.instrument_id,
            level_index=command.level_index,
            side="BUY",
            quantity=command.quantity,
            price=command.price,
        )

        self.level_positions[(command.instrument_id, command.level_index)] = trade
        self.trades.append(trade)

        print(
            f"BUY level={command.level_index} "
            f"{command.quantity} {command.instrument_id} по {command.price}"
        )

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

        key = (command.instrument_id, command.level_index)
        buy_trade = self.level_positions.get(key)

        if buy_trade is None:
            return None

        position = self.get_position(command.instrument_id)

        if position.quantity < command.quantity:
            return None

        total = command.price * command.quantity
        profit = (command.price - buy_trade.price) * command.quantity

        self.cash += total
        position.quantity -= command.quantity
        position.realized_profit += profit
        self.realized_profit += profit

        if position.quantity == 0:
            position.avg_price = Decimal("0")

        trade = VirtualTrade(
            instrument_id=command.instrument_id,
            level_index=command.level_index,
            side="SELL",
            quantity=command.quantity,
            price=command.price,
            profit=profit,
        )

        self.trades.append(trade)
        del self.level_positions[key]

        print(
            f"SELL level={command.level_index} "
            f"{command.quantity} {command.instrument_id} по {command.price}, "
            f"profit={profit}"
        )

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
        print(f"Realized profit: {self.realized_profit}")
        print("Positions:")

        for position in self.positions.values():
            print(position)

        print(f"Trades: {len(self.trades)}")

        for trade in self.trades:
            print(trade)
