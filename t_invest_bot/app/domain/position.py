from dataclasses import dataclass
from decimal import Decimal


@dataclass(slots=True)
class Position:
    instrument_id: str
    quantity: int = 0
    avg_price: Decimal = Decimal("0")
    realized_profit: Decimal = Decimal("0")
