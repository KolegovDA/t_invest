from dataclasses import dataclass
from decimal import Decimal

from strategy.trailing_engine import TrailingExitState


@dataclass(slots=True)
class OpenLevelPosition:
    level_index: int
    entry_price: Decimal
    quantity: int
    buy_commission: Decimal
    expected_sell_commission_percent: Decimal
    hard_take_profit_price: Decimal
    trailing_exit: TrailingExitState | None = None
