from decimal import Decimal, ROUND_DOWN

from t_tech.invest import Quotation


class TInvestQuotationMapper:
    nano_multiplier = Decimal("1000000000")

    def decimal_to_quotation(
        self,
        value: Decimal,
    ) -> Quotation:
        value = value.quantize(
            Decimal("0.000000001"),
            rounding=ROUND_DOWN,
        )

        units = int(value)
        nano = int(
            (value - Decimal(units))
            * self.nano_multiplier
        )

        return Quotation(
            units=units,
            nano=nano,
        )

    def quotation_to_decimal(
        self,
        quotation: Quotation,
    ) -> Decimal:
        return (
            Decimal(str(quotation.units))
            + Decimal(str(quotation.nano))
            / self.nano_multiplier
        )
