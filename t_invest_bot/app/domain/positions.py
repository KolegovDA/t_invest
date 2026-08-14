from dataclasses import dataclass
from decimal import Decimal

from strategy.trailing_engine import (
    TrailingExitState,
)


@dataclass(slots=True)
class OpenLevelPosition:
    level_index: int

    entry_price: Decimal

    #
    # Количество лотов.
    #
    quantity: int

    #
    # Фактическая или fallback
    # BUY-комиссия.
    #
    buy_commission: Decimal

    expected_sell_commission_percent: (
        Decimal
    )

    hard_take_profit_price: Decimal

    #
    # Полная фактическая стоимость
    # покупки:
    #
    # broker total_order_amount
    # +
    # buy_commission
    #
    # Для старых snapshot может
    # отсутствовать.
    #
    purchase_cost: (
        Decimal | None
    ) = None

    trailing_exit: (
        TrailingExitState | None
    ) = None
