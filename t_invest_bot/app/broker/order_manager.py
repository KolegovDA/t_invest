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
        if not self.active_commands:
            return []

        events = self.broker.execute_commands(
            commands=self.active_commands,
            current_price=current_price,
        )

        if events:
            self.active_commands.clear()

        return events
