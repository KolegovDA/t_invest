from dataclasses import dataclass
from decimal import Decimal, ROUND_FLOOR


@dataclass(slots=True)
class LevelQuantity:
    level_index: int
    target_quantity: Decimal
    actual_quantity: int
    accumulated_remainder: Decimal


@dataclass(slots=True)
class LevelQuantityCalculator:
    increase_percent_per_level: Decimal = Decimal("5")
    max_multiplier: Decimal = Decimal("3")

    def calculate(
        self,
        levels_count: int,
        base_quantity: int,
    ) -> list[LevelQuantity]:
        if levels_count <= 0:
            raise ValueError("levels_count must be greater than zero")

        if base_quantity <= 0:
            raise ValueError("base_quantity must be greater than zero")

        result: list[LevelQuantity] = []
        accumulated_remainder = Decimal("0")

        for level_index in range(1, levels_count + 1):
            target_quantity = self._calculate_target_quantity(
                level_index=level_index,
                base_quantity=base_quantity,
            )

            quantity_with_remainder = (
                target_quantity
                + accumulated_remainder
            )

            actual_quantity = int(
                quantity_with_remainder.to_integral_value(
                    rounding=ROUND_FLOOR,
                )
            )

            accumulated_remainder = (
                quantity_with_remainder
                - Decimal(actual_quantity)
            )

            result.append(
                LevelQuantity(
                    level_index=level_index,
                    target_quantity=target_quantity,
                    actual_quantity=actual_quantity,
                    accumulated_remainder=accumulated_remainder,
                )
            )

        return result

    def _calculate_target_quantity(
        self,
        level_index: int,
        base_quantity: int,
    ) -> Decimal:
        multiplier = (
            Decimal("1")
            + self.increase_percent_per_level / Decimal("100")
        ) ** Decimal(level_index - 1)

        max_quantity = (
            Decimal(base_quantity)
            * self.max_multiplier
        )

        target_quantity = (
            Decimal(base_quantity)
            * multiplier
        )

        if target_quantity > max_quantity:
            return max_quantity

        return target_quantity
