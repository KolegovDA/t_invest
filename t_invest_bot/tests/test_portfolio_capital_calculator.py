from decimal import Decimal

from application.portfolio_capital_calculator import (
    PortfolioCapitalCalculator,
)


def test_capital_calculator_returns_positive_amount() -> None:
    capital = PortfolioCapitalCalculator().calculate(
        min_price=Decimal("100"),
        max_price=Decimal("200"),
        levels_count=20,
        base_quantity=1,
    )

    assert capital > Decimal("0")
