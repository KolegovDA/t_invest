from dataclasses import dataclass
from decimal import Decimal


@dataclass(slots=True)
class TradingCommand:
    pass


@dataclass(slots=True)
class PlaceBuyLimitCommand(TradingCommand):
    instrument_id: str
    level_index: int
    quantity: int
    price: Decimal
    commission_percent: Decimal = Decimal("0.30")


@dataclass(slots=True)
class PlaceSellLimitCommand(TradingCommand):
    instrument_id: str
    level_index: int
    quantity: int
    price: Decimal
    commission_percent: Decimal = Decimal("0.30")


@dataclass(slots=True)
class PlaceSellAllLimitCommand(TradingCommand):
    instrument_id: str
    quantity: int
    price: Decimal
    reason: str = "COMPENSATION_CLOSE"
    level_index: int = 0
    commission_percent: Decimal = Decimal("0.30")


@dataclass(slots=True)
class CancelOrderCommand(TradingCommand):
    order_id: str


@dataclass(slots=True)
class ReserveCapitalCommand(TradingCommand):
    amount: Decimal


@dataclass(slots=True)
class ReleaseCapitalCommand(TradingCommand):
    amount: Decimal


@dataclass(slots=True)
class NotifyUserCommand(TradingCommand):
    message: str
