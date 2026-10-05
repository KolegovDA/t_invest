from dataclasses import (
    dataclass,
)
from decimal import (
    Decimal,
)


@dataclass(slots=True)
class BrokerCashFlow:
    """
    Внешний денежный
    поток по счёту
    у брокера
    (пополнение или
    вывод).

    Используется при
    расчёте PnL, чтобы
    не считать поток
    прибылью.
    """

    trading_account_id: str

    occurred_at: str

    kind: str

    currency: str

    payment: Decimal

    id: int | None = None
