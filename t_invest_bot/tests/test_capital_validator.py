from decimal import Decimal

from domain.entities import Instrument
from domain.enums import InstrumentType
from portfolio.capital_validator import CapitalValidator


def test_capital_validator_lot_instrument() -> None:
    instrument = Instrument(
        id="SBER",
        ticker="SBER",
        name="Sberbank",
        instrument_type=InstrumentType.STOCK,
        currency="RUB",
        lot_size=10,
        min_price_step=Decimal("0.01"),
        is_fractional=False,
    )

    validator = CapitalValidator()

    requirement = validator.calculate_required_deposit(
        instrument=instrument,
        last_price=Decimal("300"),
        levels_count=20,
    )

    assert requirement.min_order_amount == Decimal("3000")
    assert requirement.order_amount == Decimal("3000")
    assert requirement.required_deposit == Decimal("60000")


def test_capital_validator_fractional_instrument() -> None:
    instrument = Instrument(
        id="CNYRUB",
        ticker="CNYRUB",
        name="Chinese yuan",
        instrument_type=InstrumentType.CURRENCY,
        currency="RUB",
        lot_size=1,
        min_price_step=Decimal("0.0001"),
        is_fractional=True,
    )

    validator = CapitalValidator()

    requirement = validator.calculate_required_deposit(
        instrument=instrument,
        last_price=Decimal("12.5"),
        levels_count=20,
        min_fractional_order_amount=Decimal("100"),
    )

    assert requirement.min_order_amount == Decimal("100")
    assert requirement.order_amount == Decimal("120.00")
    assert requirement.required_deposit == Decimal("2400.00")


def test_capital_validator_allows_underfunded_start() -> None:
    instrument = Instrument(
        id="SBER",
        ticker="SBER",
        name="Sberbank",
        instrument_type=InstrumentType.STOCK,
        currency="RUB",
        lot_size=10,
        min_price_step=Decimal("0.01"),
        is_fractional=False,
    )

    validator = CapitalValidator()

    requirement = validator.calculate_required_deposit(
        instrument=instrument,
        last_price=Decimal("300"),
        levels_count=20,
    )

    assert validator.can_start(
        available_cash=Decimal("10000"),
        requirement=requirement,
        allow_underfunded_start=False,
    ) is False

    assert validator.can_start(
        available_cash=Decimal("10000"),
        requirement=requirement,
        allow_underfunded_start=True,
    ) is True
