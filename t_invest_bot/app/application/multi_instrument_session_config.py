from dataclasses import (
    dataclass,
    field,
)
from decimal import Decimal

from strategy.grid_engine import (
    GridEngineConfig,
)


@dataclass(slots=True)
class InstrumentConfig:
    ticker: str

    levels_count: int
    quantity: int

    history_years: int = 3

    #
    # Первую неделю истории
    # исключаем.
    #
    exclude_first_days: int = 7

    #
    # Первый BUY trailing включаем,
    # когда цена ушла от цены запуска
    # сессии минимум на ±0.50%.
    #
    first_entry_activation_percent: (
        Decimal
    ) = Decimal("0.50")

    #
    # Расстояние BUY trailing
    # под максимумом.
    #
    entry_rebound_percent: Decimal = (
        Decimal("0.15")
    )

    #
    # BUY limit ставим выше рынка.
    #
    entry_limit_offset_percent: Decimal = (
        Decimal("0.15")
    )

    #
    # SELL limit ниже рынка.
    #
    exit_limit_offset_percent: Decimal = (
        Decimal("0.15")
    )

    #
    # SELL trailing.
    #
    # По новой стратегии тоже 0.15%.
    #
    trailing_percent: Decimal = (
        Decimal("0.15")
    )

    #
    # Минимальная чистая прибыль
    # будем окончательно считать
    # следующим блоком.
    #
    min_profit_percent: Decimal = (
        Decimal("0.15")
    )

    #
    # Запас исполнения выхода:
    # trailing 0.15%
    # +
    # SELL limit 0.15%
    #
    take_profit_buffer_percent: (
        Decimal
    ) = Decimal("0.30")

    min_open_positions_for_compensation: (
        int
    ) = 5

    compensation_multiplier: Decimal = (
        Decimal("3")
    )

    def to_grid_engine_config(
        self,
    ) -> GridEngineConfig:
        return GridEngineConfig(
            quantity=(
                self.quantity
            ),

            first_entry_activation_percent=(
                self
                .first_entry_activation_percent
            ),

            entry_rebound_percent=(
                self
                .entry_rebound_percent
            ),

            entry_limit_offset_percent=(
                self
                .entry_limit_offset_percent
            ),

            exit_limit_offset_percent=(
                self
                .exit_limit_offset_percent
            ),

            trailing_percent=(
                self.trailing_percent
            ),

            min_profit_percent=(
                self.min_profit_percent
            ),

            take_profit_buffer_percent=(
                self
                .take_profit_buffer_percent
            ),

            min_open_positions_for_compensation=(
                self
                .min_open_positions_for_compensation
            ),

            compensation_multiplier=(
                self
                .compensation_multiplier
            ),
        )


@dataclass(slots=True)
class MultiInstrumentSessionConfig:
    instruments: list[
        InstrumentConfig
    ] = field(
        default_factory=list
    )

    sandbox_deposit: Decimal = (
        Decimal("100000")
    )
