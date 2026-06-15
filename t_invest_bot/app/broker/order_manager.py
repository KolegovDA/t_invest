from dataclasses import dataclass, field
from decimal import Decimal

from application.trade_capital_service import TradeCapitalService
from broker.virtual_broker import VirtualBroker
from domain.commands import (
    PlaceBuyLimitCommand,
    TradingCommand,
)
from domain.events import TradeExecutedEvent
from notifications.notifier import Notifier


@dataclass
class OrderManager:
    broker: VirtualBroker
    trade_capital_service: TradeCapitalService | None = None
    notifier: Notifier | None = None
    active_commands: list[TradingCommand] = field(default_factory=list)

    def add_commands(self, commands: list[TradingCommand]) -> None:
        self.active_commands.extend(commands)

    def process_price(self, current_price: Decimal) -> list[TradeExecutedEvent]:
        if not self.active_commands:
            return []

        executed_events: list[TradeExecutedEvent] = []
        remaining_commands: list[TradingCommand] = []

        for command in self.active_commands:
            if isinstance(command, PlaceBuyLimitCommand):
                if not self._can_execute_buy_command(command):
                    remaining_commands.append(command)
                    continue

            events = self.broker.execute_commands(
                commands=[command],
                current_price=current_price,
            )

            if events:
                executed_events.extend(events)

                for event in events:
                    if event.side == "BUY":
                        self._release_reserved_capital(event)
            else:
                remaining_commands.append(command)

        self.active_commands = remaining_commands

        return executed_events

    def _can_execute_buy_command(
        self,
        command: PlaceBuyLimitCommand,
    ) -> bool:
        if self.trade_capital_service is None:
            return True

        success = self.trade_capital_service.reserve_for_buy(
            instrument_id=command.instrument_id,
            level_index=command.level_index,
            quantity=command.quantity,
            price=command.price,
            commission_percent=self.broker.commission_percent,
        )

        if not success:
            required_amount = (
                self.trade_capital_service.calculate_required_buy_amount(
                    quantity=command.quantity,
                    price=command.price,
                    commission_percent=self.broker.commission_percent,
                )
            )

            message = (
                f"Недостаточно средств для покупки: "
                f"{command.instrument_id} level={command.level_index}, "
                f"требуется {required_amount}. "
                f"Ордер оставлен в ожидании денег."
            )

            if self.notifier is not None:
                self.notifier.notify(message)
            else:
                print(message)

        return success

    def _release_reserved_capital(
        self,
        event: TradeExecutedEvent,
    ) -> None:
        if self.trade_capital_service is None:
            return

        self.trade_capital_service.release_after_buy_execution(
            instrument_id=event.instrument_id,
            level_index=event.level_index,
        )
