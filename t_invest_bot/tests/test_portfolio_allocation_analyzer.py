from decimal import Decimal

from application.portfolio_allocation_analyzer import (
    PortfolioAllocationAnalyzer,
)
from application.portfolio_capital_plan import CapitalPlan
from application.portfolio_orchestrator import (
    InstrumentCapitalPlan,
    PortfolioStartPlan,
)


def test_allocation_analyzer_returns_percentages() -> None:
    plan = PortfolioStartPlan(
        available_cash=Decimal("100000"),
        instruments=[
            InstrumentCapitalPlan(
                ticker="SBER",
                levels_count=20,
                quantity=1,
                last_price=Decimal("300"),
                required_deposit=Decimal("10000"),
                capital_plan=CapitalPlan(),
            ),
            InstrumentCapitalPlan(
                ticker="GAZP",
                levels_count=20,
                quantity=1,
                last_price=Decimal("100"),
                required_deposit=Decimal("5000"),
                capital_plan=CapitalPlan(),
            ),
        ],
    )

    allocations = PortfolioAllocationAnalyzer().analyze(
        plan,
    )

    assert len(allocations) == 2
    assert allocations[0].ticker == "SBER"
    assert allocations[1].ticker == "GAZP"
