from dataclasses import dataclass
from decimal import Decimal


@dataclass(slots=True)
class OrderExecutionState:
    order_id: str
    is_executed: bool
    executed_quantity: int
    executed_price: Decimal | None = None
