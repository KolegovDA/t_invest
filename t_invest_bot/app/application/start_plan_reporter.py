from dataclasses import dataclass

from application.portfolio_allocation_analyzer import (
    PortfolioAllocationAnalyzer,
)
from application.portfolio_orchestrator import (
    PortfolioStartPlan,
)


@dataclass(slots=True)
class StartPlanReporter:
    def print(
        self,
        plan: PortfolioStartPlan,
    ) -> None:
        print("START PLAN")
        print("=" * 80)

        print(f"Available cash: {plan.available_cash}")
        print(f"Required cash: {plan.total_required_deposit}")
        print(f"Remaining cash: {plan.remaining_cash}")
        print(
            f"Capital utilization: "
            f"{plan.capital_utilization_percent:.2f}%"
        )
        print(f"Can start: {plan.can_start}")

        print()
        print("PORTFOLIO ALLOCATION")
        print("-" * 80)

        allocations = PortfolioAllocationAnalyzer().analyze(
            plan,
        )

        for allocation in allocations:
            print(
                f"{allocation.ticker:<10}"
                f"Capital={allocation.capital:<15}"
                f"Share={allocation.portfolio_percent:.2f}%"
            )

        print()
        print("=" * 80)

        for instrument in plan.instruments:
            print()
            print("-" * 80)
            print(f"{instrument.ticker}")
            print("-" * 80)

            print(f"Levels: {instrument.levels_count}")
            print(f"Base quantity: {instrument.quantity}")
            print(f"Current price: {instrument.last_price}")

            print()

            for level in instrument.capital_plan.levels:
                print(
                    f"Level {level.level_index:>2} | "
                    f"Price={level.price:<12} | "
                    f"Qty={level.quantity:<4} | "
                    f"Amount={level.amount}"
                )

            print()

            print(f"Gross: {instrument.capital_plan.gross_amount}")
            print(
                f"Commission: "
                f"{instrument.capital_plan.commission_amount}"
            )
            print(f"Total: {instrument.capital_plan.total_amount}")

        print()
        print("=" * 80)
