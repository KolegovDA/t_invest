from dataclasses import dataclass
from decimal import Decimal

from application.portfolio_orchestrator import (
    PortfolioStartPlan,
)


@dataclass(slots=True)
class InstrumentAllocation:
    ticker: str
    capital: Decimal
    portfolio_percent: Decimal


@dataclass(slots=True)
class PortfolioAllocationAnalyzer:
    def analyze(
        self,
        plan: PortfolioStartPlan,
    ) -> list[InstrumentAllocation]:
        total = plan.total_required_deposit

        if total <= 0:
            return []

        result: list[InstrumentAllocation] = []

        for instrument in plan.instruments:
            percent = (
                instrument.required_deposit
                / total
                * Decimal("100")
            )

            result.append(
                InstrumentAllocation(
                    ticker=instrument.ticker,
                    capital=instrument.required_deposit,
                    portfolio_percent=percent,
                )
            )

        return result
