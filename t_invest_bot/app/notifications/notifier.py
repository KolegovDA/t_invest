from dataclasses import dataclass
from typing import Protocol


class Notifier(Protocol):
    def notify(self, message: str) -> None:
        pass


@dataclass(slots=True)
class ConsoleNotifier:
    def notify(self, message: str) -> None:
        print(f"[NOTIFICATION] {message}")
