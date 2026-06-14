from dataclasses import dataclass
from decimal import Decimal


@dataclass(slots=True)
class LevelPosition:
    instrument_id: str
    level_index: int
    quantity: int
    entry_price: Decimal
    take_profit_price: Decimal
