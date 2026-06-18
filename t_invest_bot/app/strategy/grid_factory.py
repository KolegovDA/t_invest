from dataclasses import dataclass
from decimal import Decimal

from domain.entities import Candle
from strategy.grid_builder import GridBuilder
from strategy.grid_engine import GridEngine, GridEngineConfig, GridLevel
from strategy.history_analyzer import HistoryAnalyzer, PriceRange


@dataclass(slots=True)
class GridFactoryResult:
    grid_engine: GridEngine
    price_range: PriceRange
    levels: list[GridLevel]


@dataclass(slots=True)
class GridFactory:
    history_analyzer: HistoryAnalyzer

    def create_grid_engine(
        self,
        instrument_id: str,
        candles: list[Candle],
        levels_count: int,
        config: GridEngineConfig,
        current_price: Decimal | None = None,
    ) -> GridFactoryResult:
        price_range = self.history_analyzer.calculate_range(candles)

        if current_price is None:
            current_price = candles[-1].close

        builder = GridBuilder(
            levels_count=levels_count,
        )

        levels = builder.build_from_range(
            min_price=price_range.min_price,
            current_price=current_price,
        )

        grid_engine = GridEngine(
            instrument_id=instrument_id,
            levels=levels,
            config=config,
        )

        return GridFactoryResult(
            grid_engine=grid_engine,
            price_range=price_range,
            levels=levels,
        )
