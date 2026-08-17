from dataclasses import dataclass
from decimal import Decimal

from domain.entities import Candle
from strategy.grid_engine import (
    GridLevel,
)


@dataclass(slots=True)
class GridBuilder:
    levels_count: int

    #
    # Минимальный шаг сетки.
    #
    # Если исторический диапазон
    # слишком узкий, каждый следующий
    # уровень всё равно будет минимум
    # на 0.30% стартовой цены ниже.
    #
    min_step_percent: Decimal = (
        Decimal("0.30")
    )

    def build_from_candles(
        self,
        candles: list[Candle],
        current_price: Decimal,
    ) -> list[GridLevel]:
        if not candles:
            raise ValueError(
                "Candles list is empty"
            )

        min_price = min(
            candle.low
            for candle
            in candles
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
            raise ValueError(
                "levels_count must be "
                "greater than zero"
            )

        if min_price <= Decimal("0"):
            raise ValueError(
                "min_price must be "
                "greater than zero"
            )

        if current_price <= Decimal("0"):
            raise ValueError(
                "current_price must be "
                "greater than zero"
            )

        #
        # Историческая дистанция
        # от текущей цены до
        # исторического минимума.
        #
        # Если рынок уже ниже
        # исторического минимума,
        # historical_distance = 0
        # и используем минимальный
        # шаг 0.30%.
        #
        historical_distance = max(
            current_price - min_price,
            Decimal("0"),
        )

        historical_step = (
            historical_distance
            / Decimal(
                self.levels_count
            )
        )

        minimum_step = (
            current_price
            * self.min_step_percent
            / Decimal("100")
        )

        grid_step = max(
            historical_step,
            minimum_step,
        )

        levels: list[
            GridLevel
        ] = []

        #
        # Все уровни имеют
        # ОДИНАКОВЫЙ фиксированный
        # шаг.
        #
        # Именно этот шаг потом
        # будет использоваться
        # динамической логикой:
        #
        # реальная цена BUY
        # -
        # grid_step
        # =
        # следующая точка входа.
        #
        for index in range(
            1,
            self.levels_count + 1,
        ):
            price = (
                current_price
                - (
                    grid_step
                    * Decimal(index)
                )
            )

            levels.append(
                GridLevel(
                    index=index,
                    price=price,
                )
            )

        return levels

    def calculate_step(
        self,
        min_price: Decimal,
        current_price: Decimal,
    ) -> Decimal:
        """
        Возвращает фиксированный
        денежный шаг сетки.

        Нужен GridEngine для
        динамического пересчёта
        следующего уровня после
        реального исполнения BUY.
        """

        if self.levels_count <= 0:
            raise ValueError(
                "levels_count must be "
                "greater than zero"
            )

        if min_price <= Decimal("0"):
            raise ValueError(
                "min_price must be "
                "greater than zero"
            )

        if current_price <= Decimal("0"):
            raise ValueError(
                "current_price must be "
                "greater than zero"
            )

        historical_distance = max(
            current_price - min_price,
            Decimal("0"),
        )

        historical_step = (
            historical_distance
            / Decimal(
                self.levels_count
            )
        )

        minimum_step = (
            current_price
            * self.min_step_percent
            / Decimal("100")
        )

        return max(
            historical_step,
            minimum_step,
        )
