from decimal import Decimal

from application.portfolio_capital_calculator import (
    PortfolioCapitalCalculator,
)


def test_capital_plan_contains_levels() -> None:
    plan = (
        PortfolioCapitalCalculator()
        .calculate_plan(
            min_price=Decimal("100"),
            current_price=Decimal("200"),
            levels_count=10,
            base_quantity=1,
        )
    )

    assert (
        len(plan.levels)
        == 10
    )

    assert (
        plan.total_amount
        > Decimal("0")
    )

    assert (
        plan.gross_amount
        > Decimal("0")
    )

    assert (
        plan.commission_amount
        > Decimal("0")
    )


def test_capital_plan_contains_constant_step_between_levels(
) -> None:
    plan = (
        PortfolioCapitalCalculator()
        .calculate_plan(
            min_price=Decimal("100"),
            current_price=Decimal("200"),
            levels_count=10,
            base_quantity=1,
        )
    )

    first_level = (
        plan.levels[0]
    )

    second_level = (
        plan.levels[1]
    )

    third_level = (
        plan.levels[2]
    )

    assert (
        first_level.step_from_previous
        > Decimal("0")
    )

    assert (
        first_level
        .step_percent_from_previous
        >= Decimal("0.30")
    )

    #
    # Новая стратегия:
    # шаг сетки постоянный.
    #
    assert (
        second_level
        .step_from_previous
        == first_level
        .step_from_previous
    )

    assert (
        third_level
        .step_from_previous
        == second_level
        .step_from_previous
    )


def test_capital_plan_step_matches_historical_range(
) -> None:
    plan = (
        PortfolioCapitalCalculator()
        .calculate_plan(
            min_price=Decimal("100"),
            current_price=Decimal("200"),
            levels_count=10,
            base_quantity=1,
        )
    )

    #
    # Диапазон:
    #
    # 200 - 100 = 100
    #
    # 100 / 10 = 10
    #
    expected_step = Decimal(
        "10"
    )

    for level in plan.levels:
        assert (
            level.step_from_previous
            == expected_step
        )
