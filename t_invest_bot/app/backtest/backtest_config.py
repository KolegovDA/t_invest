from dataclasses import dataclass
from decimal import Decimal

from strategy.grid_engine import GridEngineConfig


@dataclass(slots=True)
class BacktestConfig:
    initial_cash: Decimal = Decimal("100000")
    levels_count: int = 5

    quantity: int = 10

    entry_limit_offset_percent: Decimal = Decimal("0.15")
    exit_limit_offset_percent: Decimal = Decimal("0.15")

    entry_rebound_percent: Decimal = Decimal("0.15")
    trailing_percent: Decimal = Decimal("0.50")

    min_profit_percent: Decimal = Decimal("0.30")
    take_profit_buffer_percent: Decimal = Decimal("0.15")

    fallback_buy_commission_percent: Decimal = Decimal("0.30")
    fallback_sell_commission_percent: Decimal = Decimal("0.30")

    min_open_positions_for_compensation: int = 5
    compensation_multiplier: Decimal = Decimal("3")

    def to_grid_engine_config(self) -> GridEngineConfig:
        return GridEngineConfig(
            entry_limit_offset_percent=self.entry_limit_offset_percent,
            exit_limit_offset_percent=self.exit_limit_offset_percent,
            entry_rebound_percent=self.entry_rebound_percent,
            trailing_percent=self.trailing_percent,
            min_profit_percent=self.min_profit_percent,
            take_profit_buffer_percent=self.take_profit_buffer_percent,
            fallback_buy_commission_percent=self.fallback_buy_commission_percent,
            fallback_sell_commission_percent=self.fallback_sell_commission_percent,
            min_open_positions_for_compensation=self.min_open_positions_for_compensation,
            compensation_multiplier=self.compensation_multiplier,
            quantity=self.quantity,
        )
