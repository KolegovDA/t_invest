from dataclasses import dataclass
from decimal import Decimal


@dataclass(slots=True)
class OrderExecutionState:
    order_id: str

    is_executed: bool

    #
    # Количество исполненных лотов.
    #
    executed_quantity: int

    #
    # Средняя фактическая цена
    # исполнения.
    #
    executed_price: (
        Decimal | None
    ) = None

    #
    # Фактическая комиссия,
    # полученная от брокера.
    #
    executed_commission: (
        Decimal | None
    ) = None

    #
    # Фактическая сумма сделки
    # без комиссии.
    #
    # Для live это значение
    # является предпочтительным
    # источником истины.
    #
    total_order_amount: (
        Decimal | None
    ) = None
