from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(slots=True)
class InstrumentConfig:
    ticker: str
    levels_count: int
    quantity: int


@dataclass(slots=True)
class MultiInstrumentSessionConfig:
    instruments: list[InstrumentConfig] = field(
        default_factory=list
    )

    sandbox_deposit: Decimal = Decimal(
        "100000"
    )
