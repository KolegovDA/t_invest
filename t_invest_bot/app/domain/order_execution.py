from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol


@dataclass(slots=True)
class PlacedOrder:
    order_id: str
    request_id: str | None = None


class OrderExecutor(Protocol):
    def place_limit_buy(
        self,
        account_id: str,
        instrument_id: str,
        quantity: int,
        price: Decimal,
    ) -> PlacedOrder:
        pass

    def place_limit_sell(
        self,
        account_id: str,
        instrument_id: str,
        quantity: int,
        price: Decimal,
    ) -> PlacedOrder:
        pass

    def cancel_order(
        self,
        account_id: str,
        order_id: str,
    ) -> None:
        pass
