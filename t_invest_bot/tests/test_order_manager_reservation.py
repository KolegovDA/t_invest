from decimal import Decimal

from application.portfolio_manager import PortfolioManager
from application.trade_capital_service import TradeCapitalService
from broker.order_manager import OrderManager
from broker.virtual_broker import VirtualBroker
from domain.commands import PlaceBuyLimitCommand
from domain.portfolio import Portfolio
from portfolio.capital_reservation_manager import CapitalReservationManager


class FakeNotifier:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def notify(self, message: str) -> None:
        self.messages.append(message)


def create_trade_capital_service(
    cash: Decimal,
) -> TradeCapitalService:
    return TradeCapitalService(
        portfolio_manager=PortfolioManager(
            portfolio=Portfolio(
                cash=cash,
            )
        ),
        reservation_manager=CapitalReservationManager(
            available_cash=cash,
        ),
    )


def test_order_manager_keeps_buy_command_when_reserve_fails() -> None:
    broker = VirtualBroker(
        cash=Decimal("100000"),
    )

    trade_capital_service = create_trade_capital_service(
        cash=Decimal("100"),
    )

    order_manager = OrderManager(
        broker=broker,
        trade_capital_service=trade_capital_service,
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

    trade_capital_service = create_trade_capital_service(
        cash=Decimal("10000"),
    )

    order_manager = OrderManager(
        broker=broker,
        trade_capital_service=trade_capital_service,
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
    assert trade_capital_service.reservation_manager.get_reserved_total() == Decimal("0")


def test_order_manager_notifies_when_reserve_fails() -> None:
    broker = VirtualBroker(
        cash=Decimal("100000"),
    )

    trade_capital_service = create_trade_capital_service(
        cash=Decimal("100"),
    )

    notifier = FakeNotifier()

    order_manager = OrderManager(
        broker=broker,
        trade_capital_service=trade_capital_service,
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
