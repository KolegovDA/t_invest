from decimal import Decimal

from portfolio.capital_validator import CapitalRequirement
from portfolio.portfolio_capital_validator import (
    PortfolioCapitalValidator,
)


def test_portfolio_capital_validator() -> None:
    requirements = [
        CapitalRequirement(
            instrument_id="SBER",
            levels_count=20,
            min_order_amount=Decimal("3000"),
            order_amount=Decimal("3000"),
            required_deposit=Decimal("60000"),
        ),
        CapitalRequirement(
            instrument_id="GAZP",
            levels_count=20,
            min_order_amount=Decimal("1900"),
            order_amount=Decimal("1900"),
            required_deposit=Decimal("38000"),
        ),
        CapitalRequirement(
            instrument_id="CNYRUB",
            levels_count=20,
            min_order_amount=Decimal("100"),
            order_amount=Decimal("120"),
            required_deposit=Decimal("2400"),
        ),
    ]

    validator = PortfolioCapitalValidator()

    result = validator.calculate(requirements)

    assert result.total_required_deposit == Decimal("100400")
    assert result.total_order_amount == Decimal("5020")

    assert result.can_start(
        available_cash=Decimal("120000")
    ) is True

    assert result.can_start(
        available_cash=Decimal("50000")
    ) is False
