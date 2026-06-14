from dataclasses import dataclass
from decimal import Decimal

from notifications.notifier import Notifier


@dataclass(slots=True)
class NotificationService:
    notifier: Notifier

    def bot_started(self) -> None:
        self.notifier.notify(
            "T-Invest Bot запущен."
        )

    def bot_stopped(self) -> None:
        self.notifier.notify(
            "T-Invest Bot остановлен."
        )

    def insufficient_funds(
        self,
        instrument_id: str,
        level_index: int,
        required_amount: Decimal,
    ) -> None:
        self.notifier.notify(
            f"Недостаточно средств для покупки: "
            f"{instrument_id}, уровень {level_index}, "
            f"требуется {required_amount}. "
            f"Ордер оставлен в ожидании денег."
        )

    def buy_executed(
        self,
        instrument_id: str,
        level_index: int,
        quantity: int,
        price: Decimal,
    ) -> None:
        self.notifier.notify(
            f"Покупка исполнена: "
            f"{instrument_id}, уровень {level_index}, "
            f"{quantity} шт. по {price}."
        )

    def sell_executed(
        self,
        instrument_id: str,
        level_index: int,
        quantity: int,
        price: Decimal,
    ) -> None:
        self.notifier.notify(
            f"Продажа исполнена: "
            f"{instrument_id}, уровень {level_index}, "
            f"{quantity} шт. по {price}."
        )

    def error(
        self,
        message: str,
    ) -> None:
        self.notifier.notify(
            f"Ошибка: {message}"
        )
