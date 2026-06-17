from dataclasses import dataclass
from decimal import Decimal

from application.level_quantity_calculator import (
    LevelQuantityCalculator,
)
from strategy.grid_builder import GridBuilder


@dataclass(slots=True)
class PortfolioCapitalCalculator:
    commission_percent: Decimal = Decimal("0.30")

    def calculate(
        self,
        min_price: Decimal,
        max_price: Decimal,
        levels_count: int,
        base_quantity: int,
    ) -> Decimal:
        levels = GridBuilder(
            levels_count=levels_count,
        ).build_from_range(
            min_price=min_price,
            max_price=max_price,
        )

        quantities = LevelQuantityCalculator().calculate(
            levels_count=levels_count,
            base_quantity=base_quantity,
        )

        gross = Decimal("0")

        for level, quantity in zip(
            levels,
            quantities,
            strict=False,
        ):
            gross += (
                level.price
                * quantity.actual_quantity
            )

        commission = (
            gross
            * self.commission_percent
            / Decimal("100")
        )

        return gross + commission
