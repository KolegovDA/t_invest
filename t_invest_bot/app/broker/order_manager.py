from dataclasses import dataclass, field
from decimal import Decimal

from broker.virtual_broker import VirtualBroker
from domain.commands import (
    PlaceBuyLimitCommand,
    TradingCommand,
)
from domain.events import TradeExecutedEvent
from notifications.notifier import Notifier
from portfolio.capital_reservation_manager import CapitalReservationManager


@dataclass
class OrderManager:
    broker: VirtualBroker
    capital_reservation_manager: CapitalReservationManager | None = None
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
        if self.capital_reservation_manager is None:
            return True

        required_amount = self._calculate_required_amount_for_buy(
            command=command,
        )

        result = self.capital_reservation_manager.reserve(
            instrument_id=command.instrument_id,
            level_index=command.level_index,
            amount=required_amount,
        )

        if not result.success:
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

        return result.success

    def _release_reserved_capital(
        self,
        event: TradeExecutedEvent,
    ) -> None:
        if self.capital_reservation_manager is None:
            return

        self.capital_reservation_manager.release(
            instrument_id=event.instrument_id,
            level_index=event.level_index,
        )

    def _calculate_required_amount_for_buy(
        self,
        command: PlaceBuyLimitCommand,
    ) -> Decimal:
        total = command.price * command.quantity
        commission = total * self.broker.commission_percent / Decimal("100")

        return total + commission
