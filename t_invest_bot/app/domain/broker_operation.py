from dataclasses import (
    dataclass,
)
from datetime import (
    datetime,
)
from decimal import (
    Decimal,
)


@dataclass(slots=True)
class BrokerOperation:
    """
    Знаковый денежный
    поток по счёту
    у брокера.

    payment > 0 —
    пополнение,

    payment < 0 —
    вывод или
    списание.
    """

    occurred_at: datetime

    kind: str

    payment: Decimal

    currency: str

    operation_id: str = ""

    instrument_id: str | None = None

    ticker: str | None = None

    quantity: Decimal | None = None
