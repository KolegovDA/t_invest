from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from domain.enums import InstrumentType


@dataclass(slots=True)
class Instrument:
    id: str
    ticker: str
    name: str

    instrument_type: InstrumentType

    currency: str

    lot_size: int
    min_price_step: Decimal

    is_fractional: bool = False


@dataclass(slots=True)
class PriceTick:
    instrument_id: str

    price: Decimal

    bid: Decimal | None = None
    ask: Decimal | None = None

    volume: int | None = None

    timestamp: datetime | None = None


@dataclass(slots=True)
class Candle:
    instrument_id: str

    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal

    volume: int

    timestamp: datetime