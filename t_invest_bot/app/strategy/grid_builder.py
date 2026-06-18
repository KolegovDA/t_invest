from dataclasses import dataclass
from decimal import Decimal

from domain.entities import Candle
from strategy.grid_engine import GridLevel


@dataclass(slots=True)
class GridBuilder:
    levels_count: int

    step_growth_percent: Decimal = Decimal("5")
    min_first_step_percent: Decimal = Decimal("0.15")

    def build_from_candles(
        self,
        candles: list[Candle],
        current_price: Decimal,
    ) -> list[GridLevel]:
        if not candles:
            raise ValueError("Candles list is empty")

        min_price = min(
            candle.low
            for candle in candles
        )

        return self.build_from_range(
            min_price=min_price,
            current_price=current_price,
        )

    def build_from_range(
        self,
        min_price: Decimal,
        current_price: Decimal,
    ) -> list[GridLevel]:
        if self.levels_count <= 0:
            raise ValueError("levels_count must be greater than zero")

        if min_price <= Decimal("0"):
            raise ValueError("min_price must be greater than zero")

        if current_price <= min_price:
            raise ValueError("current_price must be greater than min_price")

        distance = current_price - min_price

        first_step = self._calculate_first_step(
            distance=distance,
            current_price=current_price,
        )

        levels: list[GridLevel] = []
        cumulative_distance = Decimal("0")

        growth_multiplier = (
            Decimal("1")
            + self.step_growth_percent / Decimal("100")
        )

        for index in range(1, self.levels_count + 1):
            step = first_step * (
                growth_multiplier ** Decimal(index - 1)
            )

            cumulative_distance += step

            price = current_price - cumulative_distance

            levels.append(
                GridLevel(
                    index=index,
                    price=price,
                )
            )

        return levels

    def _calculate_first_step(
        self,
        distance: Decimal,
        current_price: Decimal,
    ) -> Decimal:
        growth_multiplier = (
            Decimal("1")
            + self.step_growth_percent / Decimal("100")
        )

        growth_sum = sum(
            (
                growth_multiplier ** Decimal(index)
                for index in range(self.levels_count)
            ),
            start=Decimal("0"),
        )

        calculated_first_step = distance / growth_sum

        min_first_step = (
            current_price
            * self.min_first_step_percent
            / Decimal("100")
        )

        if calculated_first_step < min_first_step:
            return min_first_step

        return calculated_first_step
