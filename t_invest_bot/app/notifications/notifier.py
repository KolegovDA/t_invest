from dataclasses import dataclass
from typing import Protocol


class Notifier(Protocol):
    def notify(self, message: str) -> object:
        pass


@dataclass(slots=True)
class ConsoleNotifier:
    def notify(self, message: str) -> None:
        print(f"[NOTIFICATION] {message}")


@dataclass(slots=True)
class CompositeNotifier:
    # Рассылает сообщение
    # сразу в несколько
    # каналов (Web Push,
    # ntfy и т. д.).
    notifiers: list

    def notify(self, message: str) -> None:
        for notifier in self.notifiers:
            notifier.notify(message)
