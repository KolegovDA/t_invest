from decimal import Decimal

from notifications.notification_service import NotificationService


class FakeNotifier:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def notify(self, message: str) -> None:
        self.messages.append(message)


def test_notification_service_sends_insufficient_funds_message() -> None:
    notifier = FakeNotifier()
    service = NotificationService(notifier=notifier)

    service.insufficient_funds(
        instrument_id="SBER",
        level_index=1,
        required_amount=Decimal("3000"),
    )

    assert len(notifier.messages) == 1
    assert "Недостаточно средств" in notifier.messages[0]
    assert "SBER" in notifier.messages[0]


def test_notification_service_sends_trade_messages() -> None:
    notifier = FakeNotifier()
    service = NotificationService(notifier=notifier)

    service.buy_executed(
        instrument_id="SBER",
        level_index=1,
        quantity=10,
        price=Decimal("300"),
    )

    service.sell_executed(
        instrument_id="SBER",
        level_index=1,
        quantity=10,
        price=Decimal("303"),
    )

    assert len(notifier.messages) == 2
    assert "Покупка исполнена" in notifier.messages[0]
    assert "Продажа исполнена" in notifier.messages[1]
