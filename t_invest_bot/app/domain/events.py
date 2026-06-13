from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class TradeExecutedEvent:
    instrument_id: str
    side: str
    quantity: int
    price: Decimal
