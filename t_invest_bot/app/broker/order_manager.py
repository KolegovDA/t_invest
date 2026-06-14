from dataclasses import dataclass, field
from decimal import Decimal

from broker.virtual_broker import VirtualBroker
from domain.commands import (
    PlaceBuyLimitCommand,
    PlaceSellAllLimitCommand,
    PlaceSellLimitCommand,
    TradingCommand,
)
from domain.events import TradeExecutedEvent


@dataclass
class OrderManager:
    broker: VirtualBroker
    active_commands: list[TradingCommand] = field(default_factory=list)

    def add_commands(self, commands: list[TradingCommand]) -> None:
        self.active_commands.extend(commands)

    def process_price(self, current_price: Decimal) -> list[TradeExecutedEvent]:
        if not self.active_commands:
            return []

        executed_events: list[TradeExecutedEvent] = []
        remaining_commands: list[TradingCommand] = []

        for command in self.active_commands:
            events = self.broker.execute_commands(
                commands=[command],
                current_price=current_price,
            )

            if events:
                executed_events.extend(events)
            else:
                remaining_commands.append(command)

        self.active_commands = remaining_commands

        return executed_events
