from dataclasses import dataclass

from application.portfolio_allocation_analyzer import PortfolioAllocationAnalyzer
from application.portfolio_orchestrator import PortfolioStartPlan


@dataclass(slots=True)
class StartPlanReporter:
    def print(self, plan: PortfolioStartPlan) -> None:
        print("START PLAN")
        print("=" * 100)

        print(f"Available cash: {plan.available_cash}")
        print(f"Required cash: {plan.total_required_deposit}")
        print(f"Remaining cash: {plan.remaining_cash}")
        print(f"Missing cash: {plan.missing_cash}")
        print(f"Capital utilization: {plan.capital_utilization_percent:.2f}%")
        print(f"Can start: {plan.can_start}")
        print(f"Can start forced: {plan.can_start_forced}")

        if plan.warning_message:
            print()
            print("WARNING:")
            print(plan.warning_message)

        print()
        print("PORTFOLIO ALLOCATION")
        print("-" * 100)

        for allocation in PortfolioAllocationAnalyzer().analyze(plan):
            print(
                f"{allocation.ticker:<10}"
                f"Capital={allocation.capital:<15}"
                f"Share={allocation.portfolio_percent:.2f}%"
            )

        print()
        print("=" * 100)

        for instrument in plan.instruments:
            print()
            print("-" * 100)
            print(f"{instrument.ticker}")
            print("-" * 100)

            print(f"Levels: {instrument.levels_count}")
            print(f"Base quantity: {instrument.quantity}")
            print(f"Current price: {instrument.last_price}")
            print()

            for level in instrument.capital_plan.levels:
                print(
                    f"Level {level.level_index:>2} | "
                    f"Price={level.price:<14} | "
                    f"Step={level.step_from_previous:<14} | "
                    f"Step%={level.step_percent_from_previous:.4f}% | "
                    f"Qty={level.quantity:<4} | "
                    f"Amount={level.amount}"
                )

            print()
            print(f"Gross: {instrument.capital_plan.gross_amount}")
            print(f"Commission: {instrument.capital_plan.commission_amount}")
            print(f"Total: {instrument.capital_plan.total_amount}")

        print()
        print("=" * 100)
