from dataclasses import (
    dataclass,
)
from decimal import (
    Decimal,
)


@dataclass(slots=True)
class MoneyMovement:
    """
    Движение средств по счёту.

    amount > 0 — пополнение,
    amount < 0 — вывод.
    """

    created_at: str

    trading_account_id: str

    amount: Decimal

    note: str = ""

    id: int | None = None
