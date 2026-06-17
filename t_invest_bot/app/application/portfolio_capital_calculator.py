from dataclasses import dataclass
from decimal import Decimal

from application.level_quantity_calculator import (
    LevelQuantityCalculator,
)
from application.portfolio_capital_plan import (
    CapitalLevelPlan,
    CapitalPlan,
)
from strategy.grid_builder import GridBuilder


@dataclass(slots=True)
class PortfolioCapitalCalculator:
    commission_percent: Decimal = Decimal("0.30")

    def calculate_plan(
        self,
        min_price: Decimal,
        max_price: Decimal,
        levels_count: int,
        base_quantity: int,
    ) -> CapitalPlan:
        levels = GridBuilder(
            levels_count=levels_count,
        ).build_from_range(
            min_price=min_price,
            max_price=max_price,
        )

        quantities = (
            LevelQuantityCalculator()
            .calculate(
                levels_count=levels_count,
                base_quantity=base_quantity,
            )
        )

        level_plans: list[CapitalLevelPlan] = []

        gross = Decimal("0")

        for level, quantity in zip(
            levels,
            quantities,
            strict=False,
        ):
            amount = (
                level.price
                * quantity.actual_quantity
            )

            gross += amount

            level_plans.append(
                CapitalLevelPlan(
                    level_index=level.index,
                    price=level.price,
                    quantity=quantity.actual_quantity,
                    amount=amount,
                )
            )

        commission = (
            gross
            * self.commission_percent
            / Decimal("100")
        )

        return CapitalPlan(
            levels=level_plans,
            gross_amount=gross,
            commission_amount=commission,
            total_amount=gross + commission,
        )

    def calculate(
        self,
        min_price: Decimal,
        max_price: Decimal,
        levels_count: int,
        base_quantity: int,
    ) -> Decimal:
        return self.calculate_plan(
            min_price=min_price,
            max_price=max_price,
            levels_count=levels_count,
            base_quantity=base_quantity,
        ).total_amount
