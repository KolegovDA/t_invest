from decimal import Decimal

from application.portfolio_capital_plan import (
    CapitalLevelPlan,
    CapitalPlan,
)
from application.portfolio_orchestrator import (
    InstrumentCapitalPlan,
    PortfolioStartPlan,
)
from application.start_plan_reporter import (
    StartPlanReporter,
)


def test_start_plan_reporter_prints_without_error() -> None:
    reporter = StartPlanReporter()

    plan = PortfolioStartPlan(
        available_cash=Decimal("100000"),
        instruments=[
            InstrumentCapitalPlan(
                ticker="SBER",
                levels_count=2,
                quantity=1,
                last_price=Decimal("300"),
                required_deposit=Decimal("1000"),
                capital_plan=CapitalPlan(
                    levels=[
                        CapitalLevelPlan(
                            level_index=1,
                            price=Decimal("300"),
                            quantity=1,
                            amount=Decimal("300"),
                        )
                    ],
                    gross_amount=Decimal("300"),
                    commission_amount=Decimal("1"),
                    total_amount=Decimal("301"),
                ),
                historical_min_price=Decimal("0"),
                historical_max_price=Decimal("0"),
            )
        ],
    )

    reporter.print(plan)
