from decimal import Decimal

from application.portfolio_capital_calculator import (
    PortfolioCapitalCalculator,
)


def test_capital_plan_contains_levels() -> None:
    plan = PortfolioCapitalCalculator().calculate_plan(
        min_price=Decimal("100"),
        max_price=Decimal("200"),
        levels_count=10,
        base_quantity=1,
    )

    assert len(plan.levels) == 10
    assert plan.total_amount > Decimal("0")
    assert plan.gross_amount > Decimal("0")
    assert plan.commission_amount > Decimal("0")
