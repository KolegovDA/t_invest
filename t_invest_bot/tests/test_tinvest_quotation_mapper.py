from decimal import Decimal

from infrastructure.tinvest.quotation_mapper import TInvestQuotationMapper


def test_decimal_to_quotation() -> None:
    mapper = TInvestQuotationMapper()

    quotation = mapper.decimal_to_quotation(
        Decimal("322.04"),
    )

    assert quotation.units == 322
    assert quotation.nano == 40000000


def test_quotation_to_decimal() -> None:
    mapper = TInvestQuotationMapper()

    quotation = mapper.decimal_to_quotation(
        Decimal("322.04"),
    )

    value = mapper.quotation_to_decimal(
        quotation,
    )

    assert value == Decimal("322.04")
