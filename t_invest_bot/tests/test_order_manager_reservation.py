from decimal import Decimal

from broker.order_manager import OrderManager
from broker.virtual_broker import VirtualBroker
from domain.commands import PlaceBuyLimitCommand
from portfolio.capital_reservation_manager import CapitalReservationManager


class FakeNotifier:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def notify(self, message: str) -> None:
        self.messages.append(message)


def test_order_manager_keeps_buy_command_when_reserve_fails() -> None:
    broker = VirtualBroker(
        cash=Decimal("100000"),
    )

    reservation_manager = CapitalReservationManager(
        available_cash=Decimal("100"),
    )

    order_manager = OrderManager(
        broker=broker,
        capital_reservation_manager=reservation_manager,
    )

    command = PlaceBuyLimitCommand(
        instrument_id="SBER",
        level_index=1,
        quantity=10,
        price=Decimal("300"),
    )

    order_manager.add_commands([command])

    events = order_manager.process_price(
        current_price=Decimal("299"),
    )

    assert events == []
    assert order_manager.active_commands == [command]
    assert broker.trades == []


def test_order_manager_executes_buy_when_reserve_succeeds() -> None:
    broker = VirtualBroker(
        cash=Decimal("100000"),
    )

    reservation_manager = CapitalReservationManager(
        available_cash=Decimal("10000"),
    )

    order_manager = OrderManager(
        broker=broker,
        capital_reservation_manager=reservation_manager,
    )

    command = PlaceBuyLimitCommand(
        instrument_id="SBER",
        level_index=1,
        quantity=10,
        price=Decimal("300"),
    )

    order_manager.add_commands([command])

    events = order_manager.process_price(
        current_price=Decimal("299"),
    )

    assert len(events) == 1
    assert events[0].side == "BUY"
    assert order_manager.active_commands == []
    assert len(broker.trades) == 1


def test_order_manager_notifies_when_reserve_fails() -> None:
    broker = VirtualBroker(
        cash=Decimal("100000"),
    )

    reservation_manager = CapitalReservationManager(
        available_cash=Decimal("100"),
    )

    notifier = FakeNotifier()

    order_manager = OrderManager(
        broker=broker,
        capital_reservation_manager=reservation_manager,
        notifier=notifier,
    )

    command = PlaceBuyLimitCommand(
        instrument_id="SBER",
        level_index=1,
        quantity=10,
        price=Decimal("300"),
    )

    order_manager.add_commands([command])

    events = order_manager.process_price(
        current_price=Decimal("299"),
    )

    assert events == []
    assert len(notifier.messages) == 1
    assert "Недостаточно средств" in notifier.messages[0]
