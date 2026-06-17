from decimal import Decimal

from application.level_quantity_calculator import LevelQuantityCalculator


def test_level_quantity_calculator_increases_quantity_by_5_percent() -> None:
    calculator = LevelQuantityCalculator(
        increase_percent_per_level=Decimal("5"),
    )

    quantities = calculator.calculate(
        levels_count=3,
        base_quantity=10,
    )

    assert quantities[0].target_quantity == Decimal("10")
    assert quantities[1].target_quantity == Decimal("10.50")
    assert quantities[2].target_quantity == Decimal("11.0250")


def test_level_quantity_calculator_accumulates_remainder() -> None:
    calculator = LevelQuantityCalculator(
        increase_percent_per_level=Decimal("5"),
    )

    quantities = calculator.calculate(
        levels_count=10,
        base_quantity=1,
    )

    actual_quantities = [
        quantity.actual_quantity
        for quantity in quantities
    ]

    assert actual_quantities == [
        1,
        1,
        1,
        1,
        1,
        1,
        2,
        1,
        2,
        1,
    ]


def test_level_quantity_calculator_limits_target_quantity_by_max_multiplier() -> None:
    calculator = LevelQuantityCalculator(
        increase_percent_per_level=Decimal("100"),
        max_multiplier=Decimal("3"),
    )

    quantities = calculator.calculate(
        levels_count=5,
        base_quantity=10,
    )

    target_quantities = [
        quantity.target_quantity
        for quantity in quantities
    ]

    assert target_quantities == [
        Decimal("10"),
        Decimal("20"),
        Decimal("30"),
        Decimal("30"),
        Decimal("30"),
    ]


def test_level_quantity_calculator_rejects_invalid_levels_count() -> None:
    calculator = LevelQuantityCalculator()

    try:
        calculator.calculate(
            levels_count=0,
            base_quantity=1,
        )
    except ValueError as error:
        assert str(error) == "levels_count must be greater than zero"
    else:
        raise AssertionError("ValueError was not raised")


def test_level_quantity_calculator_rejects_invalid_base_quantity() -> None:
    calculator = LevelQuantityCalculator()

    try:
        calculator.calculate(
            levels_count=1,
            base_quantity=0,
        )
    except ValueError as error:
        assert str(error) == "base_quantity must be greater than zero"
    else:
        raise AssertionError("ValueError was not raised")
