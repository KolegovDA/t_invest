from dataclasses import dataclass

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
        print("=" * 60)

        print(
            f"Available cash: {plan.available_cash}"
        )
        print(
            f"Required cash: {plan.total_required_deposit}"
        )
        print(
            f"Can start: {plan.can_start}"
        )

        print()

        for instrument in plan.instruments:
            print("-" * 60)
            print(
                f"{instrument.ticker}"
            )
            print("-" * 60)

            for level in instrument.capital_plan.levels:
                print(
                    f"Level {level.level_index:>2} | "
                    f"Price={level.price} | "
                    f"Qty={level.quantity} | "
                    f"Amount={level.amount}"
                )

            print()

            print(
                f"Gross: {instrument.capital_plan.gross_amount}"
            )
            print(
                f"Commission: "
                f"{instrument.capital_plan.commission_amount}"
            )
            print(
                f"Total: "
                f"{instrument.capital_plan.total_amount}"
            )

            print()

        print("=" * 60)
