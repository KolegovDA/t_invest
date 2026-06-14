from dataclasses import dataclass, field
from decimal import Decimal

from portfolio.capital_validator import CapitalRequirement


@dataclass(slots=True)
class PortfolioCapitalRequirement:
    requirements: list[CapitalRequirement] = field(default_factory=list)

    total_required_deposit: Decimal = Decimal("0")
    total_order_amount: Decimal = Decimal("0")

    def can_start(
        self,
        available_cash: Decimal,
    ) -> bool:
        return available_cash >= self.total_required_deposit


@dataclass(slots=True)
class PortfolioCapitalValidator:
    def calculate(
        self,
        requirements: list[CapitalRequirement],
    ) -> PortfolioCapitalRequirement:
        total_required_deposit = sum(
            (
                requirement.required_deposit
                for requirement in requirements
            ),
            Decimal("0"),
        )

        total_order_amount = sum(
            (
                requirement.order_amount
                for requirement in requirements
            ),
            Decimal("0"),
        )

        return PortfolioCapitalRequirement(
            requirements=requirements,
            total_required_deposit=total_required_deposit,
            total_order_amount=total_order_amount,
        )
