from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol


@dataclass(slots=True)
class PlacedOrder:
    order_id: str
    request_id: str | None = None
    reason: str | None = None


@dataclass(slots=True)
class BrokerActiveOrder:
    order_id: str

    instrument_id: str

    # "BUY" | "SELL"
    direction: str

    quantity_lots: int | Decimal

    price: Decimal


def require_integer_lots(quantity: int | Decimal) -> int:
    value = Decimal(quantity)
    if not value.is_finite() or value <= 0 or value != value.to_integral_value():
        raise ValueError("T-Invest order quantity must be a positive integer number of lots")
    return int(value)


class OrderExecutor(Protocol):
    def place_limit_buy(
        self,
        account_id: str,
        instrument_id: str,
        quantity: int | Decimal,
        price: Decimal,
    ) -> PlacedOrder:
        pass

    def place_limit_sell(
        self,
        account_id: str,
        instrument_id: str,
        quantity: int | Decimal,
        price: Decimal,
    ) -> PlacedOrder:
        pass

    def cancel_order(
        self,
        account_id: str,
        order_id: str,
    ) -> None:
        pass
