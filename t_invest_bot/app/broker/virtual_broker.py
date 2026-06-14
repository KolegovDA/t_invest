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
    commission: Decimal = Decimal("0")
    profit: Decimal = Decimal("0")


@dataclass
class VirtualLevelPosition:
    instrument_id: str
    level_index: int
    quantity: int
    entry_price: Decimal
    buy_commission: Decimal


@dataclass
class VirtualBroker:
    cash: Decimal
    commission_percent: Decimal = Decimal("0.30")

    realized_profit: Decimal = Decimal("0")
    trades: List[VirtualTrade] = field(default_factory=list)
    level_positions: dict[tuple[str, int], VirtualLevelPosition] = field(default_factory=dict)

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
        commission = self._calculate_commission(total)
        total_with_commission = total + commission

        if self.cash < total_with_commission:
            print("Недостаточно виртуальных денег")
            return None

        self.cash -= total_with_commission

        key = (command.instrument_id, command.level_index)
        self.level_positions[key] = VirtualLevelPosition(
            instrument_id=command.instrument_id,
            level_index=command.level_index,
            quantity=command.quantity,
            entry_price=command.price,
            buy_commission=commission,
        )

        trade = VirtualTrade(
            instrument_id=command.instrument_id,
            level_index=command.level_index,
            side="BUY",
            quantity=command.quantity,
            price=command.price,
            commission=commission,
        )

        self.trades.append(trade)

        print(
            f"BUY level={command.level_index} "
            f"{command.quantity} {command.instrument_id} по {command.price}, "
            f"commission={commission}"
        )

        return TradeExecutedEvent(
            instrument_id=command.instrument_id,
            level_index=command.level_index,
            side="BUY",
            quantity=command.quantity,
            price=command.price,
            commission=commission,
        )

    def execute_sell_limit(
        self,
        command: PlaceSellLimitCommand,
        current_price: Decimal,
    ) -> TradeExecutedEvent | None:
        if current_price < command.price:
            return None

        key = (command.instrument_id, command.level_index)
        position = self.level_positions.get(key)

        if position is None:
            return None

        if position.quantity < command.quantity:
            return None

        total = command.price * command.quantity
        sell_commission = self._calculate_commission(total)

        buy_total = position.entry_price * position.quantity
        sell_total_after_commission = total - sell_commission

        profit = sell_total_after_commission - buy_total - position.buy_commission

        self.cash += sell_total_after_commission
        self.realized_profit += profit

        trade = VirtualTrade(
            instrument_id=command.instrument_id,
            level_index=command.level_index,
            side="SELL",
            quantity=command.quantity,
            price=command.price,
            commission=sell_commission,
            profit=profit,
        )

        self.trades.append(trade)
        del self.level_positions[key]

        print(
            f"SELL level={command.level_index} "
            f"{command.quantity} {command.instrument_id} по {command.price}, "
            f"commission={sell_commission}, "
            f"profit={profit}"
        )

        return TradeExecutedEvent(
            instrument_id=command.instrument_id,
            level_index=command.level_index,
            side="SELL",
            quantity=command.quantity,
            price=command.price,
            commission=sell_commission,
        )

    def summary(self) -> None:
        print("----- VIRTUAL BROKER -----")
        print(f"Cash: {self.cash}")
        print(f"Realized profit: {self.realized_profit}")

        print("Open level positions:")
        for position in self.level_positions.values():
            print(
                f"{position.instrument_id} level={position.level_index}: "
                f"quantity={position.quantity}, "
                f"entry_price={position.entry_price}, "
                f"buy_commission={position.buy_commission}"
            )

        print(f"Trades: {len(self.trades)}")
        for trade in self.trades:
            print(trade)

    def _calculate_commission(self, amount: Decimal) -> Decimal:
        return amount * self.commission_percent / Decimal("100")
