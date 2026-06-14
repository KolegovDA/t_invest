from dataclasses import dataclass
from decimal import Decimal

from broker.virtual_broker import VirtualBroker
from domain.commands import PlaceBuyLimitCommand, TradingCommand


@dataclass(slots=True)
class RiskManagerConfig:
    max_position_value_per_instrument: Decimal
    max_total_position_value: Decimal


@dataclass(slots=True)
class RiskManager:
    broker: VirtualBroker
    config: RiskManagerConfig

    def filter_commands(
        self,
        commands: list[TradingCommand],
    ) -> list[TradingCommand]:
        approved_commands: list[TradingCommand] = []

        for command in commands:
            if isinstance(command, PlaceBuyLimitCommand):
                if not self.can_buy(command):
                    print(
                        f"RISK BLOCK BUY: "
                        f"{command.instrument_id} level={command.level_index} "
                        f"quantity={command.quantity} price={command.price}"
                    )
                    continue

            approved_commands.append(command)

        return approved_commands

    def can_buy(self, command: PlaceBuyLimitCommand) -> bool:
        new_order_value = command.price * command.quantity

        current_instrument_value = self.get_instrument_position_value(
            command.instrument_id
        )

        if (
            current_instrument_value + new_order_value
            > self.config.max_position_value_per_instrument
        ):
            return False

        current_total_value = self.get_total_position_value()

        if (
            current_total_value + new_order_value
            > self.config.max_total_position_value
        ):
            return False

        return True

    def get_instrument_position_value(self, instrument_id: str) -> Decimal:
        position = self.broker.positions.get(instrument_id)

        if position is None:
            return Decimal("0")

        return position.avg_price * position.quantity

    def get_total_position_value(self) -> Decimal:
        total = Decimal("0")

        for position in self.broker.positions.values():
            total += position.avg_price * position.quantity

        return total
