from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class TradeExecutedEvent:
    instrument_id: str
    level_index: int

    side: str

    #
    # Количество лотов.
    #
    quantity: int

    #
    # Фактическая средняя
    # цена исполнения.
    #
    price: Decimal

    #
    # Фактическая комиссия.
    #
    commission: (
        Decimal | None
    ) = None

    #
    # Фактическая сумма сделки
    # без комиссии.
    #
    total_amount: (
        Decimal | None
    ) = None
