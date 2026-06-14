from dataclasses import dataclass, field
from decimal import Decimal

from broker.virtual_broker import VirtualBroker
from domain.commands import TradingCommand
from domain.events import TradeExecutedEvent


@dataclass
class OrderManager:
    broker: VirtualBroker
    active_commands: list[TradingCommand] = field(default_factory=list)

    def add_commands(self, commands: list[TradingCommand]) -> None:
        self.active_commands.extend(commands)

    def process_price(self, current_price: Decimal) -> list[TradeExecutedEvent]:
        events = self.broker.execute_commands(
            commands=self.active_commands,
            current_price=current_price,
        )

        self._remove_executed_commands(events)

        return events

    def _remove_executed_commands(self, events: list[TradeExecutedEvent]) -> None:
        executed_commands: list[TradingCommand] = []

        for event in events:
            for command in self.active_commands:
                if (
                    command.instrument_id == event.instrument_id
                    and command.level_index == event.level_index
                    and command.quantity == event.quantity
                    and command.price == event.price
                ):
                    executed_commands.append(command)
                    break

        for command in executed_commands:
            if command in self.active_commands:
                self.active_commands.remove(command)
