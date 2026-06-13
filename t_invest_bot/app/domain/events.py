from dataclasses import dataclass
from decimal import Decimal


@dataclass(slots=True, frozen=True)
class TradeExecutedEvent:
    instrument_id: str
    level_index: int
    side: str
    quantity: int
    price: Decimal
