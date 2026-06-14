from dataclasses import dataclass
from decimal import Decimal

from domain.entities import Instrument


@dataclass(slots=True)
class CapitalRequirement:
    instrument_id: str
    levels_count: int

    min_order_amount: Decimal
    order_amount: Decimal
    required_deposit: Decimal


@dataclass(slots=True)
class CapitalValidator:
    fractional_order_multiplier: Decimal = Decimal("1.20")

    def calculate_required_deposit(
        self,
        instrument: Instrument,
        last_price: Decimal,
        levels_count: int,
        min_fractional_order_amount: Decimal | None = None,
    ) -> CapitalRequirement:
        if levels_count <= 0:
            raise ValueError("levels_count must be greater than zero")

        if last_price <= Decimal("0"):
            raise ValueError("last_price must be greater than zero")

        if instrument.is_fractional:
            if min_fractional_order_amount is None:
                raise ValueError("min_fractional_order_amount is required for fractional instrument")

            min_order_amount = min_fractional_order_amount
            order_amount = min_order_amount * self.fractional_order_multiplier
        else:
            min_order_amount = last_price * Decimal(instrument.lot_size)
            order_amount = min_order_amount

        required_deposit = order_amount * Decimal(levels_count)

        return CapitalRequirement(
            instrument_id=instrument.id,
            levels_count=levels_count,
            min_order_amount=min_order_amount,
            order_amount=order_amount,
            required_deposit=required_deposit,
        )

    def can_start(
        self,
        available_cash: Decimal,
        requirement: CapitalRequirement,
        allow_underfunded_start: bool = False,
    ) -> bool:
        if available_cash >= requirement.required_deposit:
            return True

        return allow_underfunded_start
