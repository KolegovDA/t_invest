from dataclasses import dataclass
from decimal import Decimal


@dataclass(slots=True)
class InstrumentStatistics:
    instrument_id: str

    total_cycles: int = 0

    profitable_cycles: int = 0
    losing_cycles: int = 0

    total_profit: Decimal = Decimal("0")

    max_drawdown: Decimal = Decimal("0")

    average_cycle_profit: Decimal = Decimal("0")

    compensation_closes: int = 0

    total_trades: int = 0
