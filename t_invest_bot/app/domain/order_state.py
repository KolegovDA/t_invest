from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(slots=True)
class OrderExecutionState:
    order_id: str

    #
    # Полное исполнение заявки.
    #
    is_executed: bool

    #
    # Количество фактически
    # исполненных лотов.
    #
    executed_quantity: int

    executed_price: (
        Decimal | None
    ) = None

    executed_commission: (
        Decimal | None
    ) = None

    total_order_amount: (
        Decimal | None
    ) = None

    #
    # Нормализованный статус брокера:
    #
    # NEW
    # PARTIALLY_FILLED
    # FILLED
    # CANCELLED
    # REJECTED
    # UNKNOWN
    #
    status: str = "UNKNOWN"

    is_cancelled: bool = False
    is_rejected: bool = False

    @property
    def is_terminal_without_execution(
        self,
    ) -> bool:
        return (
            self.is_cancelled
            or self.is_rejected
        )
