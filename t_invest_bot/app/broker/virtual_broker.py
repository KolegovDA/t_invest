from dataclasses import dataclass, field
from decimal import Decimal
from typing import List

from domain.commands import (
    PlaceBuyLimitCommand,
    PlaceSellAllLimitCommand,
    PlaceSellLimitCommand,
    TradingCommand,
)
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

            elif isinstance(command, PlaceSellAllLimitCommand):
                sell_all_events = self.execute_sell_all_limit(command, current_price)
                events.extend(sell_all_events)

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

        event = self._close_level_position(
            position=position,
            sell_price=command.price,
            quantity=command.quantity,
        )

        del self.level_positions[key]

        return event

    def execute_sell_all_limit(
        self,
        command: PlaceSellAllLimitCommand,
        current_price: Decimal,
    ) -> list[TradeExecutedEvent]:
        if current_price < command.price:
            return []

        positions_to_close = [
            position
            for position in self.level_positions.values()
            if position.instrument_id == command.instrument_id
        ]

        total_available_quantity = sum(position.quantity for position in positions_to_close)

        if total_available_quantity <= 0:
            return []

        if command.quantity > total_available_quantity:
            return []

        events: list[TradeExecutedEvent] = []

        for position in positions_to_close:
            event = self._close_level_position(
                position=position,
                sell_price=command.price,
                quantity=position.quantity,
            )

            events.append(event)

            key = (position.instrument_id, position.level_index)
            del self.level_positions[key]

        return events

    def calculate_market_value(
        self,
        current_price: Decimal,
        instrument_id: str | None = None,
    ) -> Decimal:
        market_value = Decimal("0")

        for position in self.level_positions.values():
            if instrument_id is not None and position.instrument_id != instrument_id:
                continue

            market_value += current_price * position.quantity

        return market_value

    def calculate_equity(
        self,
        current_price: Decimal,
        instrument_id: str | None = None,
    ) -> Decimal:
        return self.cash + self.calculate_market_value(
            current_price=current_price,
            instrument_id=instrument_id,
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

    def _close_level_position(
        self,
        position: VirtualLevelPosition,
        sell_price: Decimal,
        quantity: int,
    ) -> TradeExecutedEvent:
        total = sell_price * quantity
        sell_commission = self._calculate_commission(total)

        buy_total = position.entry_price * quantity
        sell_total_after_commission = total - sell_commission

        profit = sell_total_after_commission - buy_total - position.buy_commission

        self.cash += sell_total_after_commission
        self.realized_profit += profit

        trade = VirtualTrade(
            instrument_id=position.instrument_id,
            level_index=position.level_index,
            side="SELL",
            quantity=quantity,
            price=sell_price,
            commission=sell_commission,
            profit=profit,
        )

        self.trades.append(trade)

        print(
            f"SELL level={position.level_index} "
            f"{quantity} {position.instrument_id} по {sell_price}, "
            f"commission={sell_commission}, "
            f"profit={profit}"
        )

        return TradeExecutedEvent(
            instrument_id=position.instrument_id,
            level_index=position.level_index,
            side="SELL",
            quantity=quantity,
            price=sell_price,
            commission=sell_commission,
        )

    def _calculate_commission(self, amount: Decimal) -> Decimal:
        return amount * self.commission_percent / Decimal("100")
