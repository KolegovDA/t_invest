from dataclasses import (
    dataclass,
)
from decimal import (
    Decimal,
)


@dataclass(slots=True)
class BalanceSnapshot:
    """
    Реальный баланс счёта
    у брокера на момент
    снапшота.

    equity = cash + market_value
    по данным брокера.
    """

    created_at: str

    trading_account_id: str

    currency: str

    equity: Decimal

    id: int | None = None
