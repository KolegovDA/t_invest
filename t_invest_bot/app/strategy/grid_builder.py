from dataclasses import dataclass
from decimal import Decimal

from domain.entities import Candle
from strategy.grid_engine import GridLevel


@dataclass(slots=True)
class GridBuilder:
    levels_count: int

    def build_from_candles(self, candles: list[Candle]) -> list[GridLevel]:
        if not candles:
            raise ValueError("Candles list is empty")

        if self.levels_count <= 0:
            raise ValueError("levels_count must be greater than zero")

        min_price = min(candle.low for candle in candles)
        max_price = max(candle.high for candle in candles)

        return self.build_from_range(
            min_price=min_price,
            max_price=max_price,
        )

    def build_from_range(
        self,
        min_price: Decimal,
        max_price: Decimal,
    ) -> list[GridLevel]:
        if min_price <= Decimal("0"):
            raise ValueError("min_price must be greater than zero")

        if max_price <= min_price:
            raise ValueError("max_price must be greater than min_price")

        step = (max_price - min_price) / Decimal(self.levels_count)

        levels: list[GridLevel] = []

        for index in range(1, self.levels_count + 1):
            price = max_price - step * Decimal(index)

            levels.append(
                GridLevel(
                    index=index,
                    price=price,
                )
            )

        return levels
