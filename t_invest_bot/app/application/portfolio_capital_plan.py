from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(slots=True)
class CapitalLevelPlan:
    level_index: int
    price: Decimal
    quantity: int
    amount: Decimal


@dataclass(slots=True)
class CapitalPlan:
    levels: list[CapitalLevelPlan] = field(
        default_factory=list
    )

    gross_amount: Decimal = Decimal("0")
    commission_amount: Decimal = Decimal("0")
    total_amount: Decimal = Decimal("0")
    from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(slots=True)
class CapitalLevelPlan:
    level_index: int
    price: Decimal
    quantity: int
    amount: Decimal
    step_from_previous: Decimal = Decimal("0")
    step_percent_from_previous: Decimal = Decimal("0")


@dataclass(slots=True)
class CapitalPlan:
    levels: list[CapitalLevelPlan] = field(default_factory=list)

    gross_amount: Decimal = Decimal("0")
    commission_amount: Decimal = Decimal("0")
    total_amount: Decimal = Decimal("0")
