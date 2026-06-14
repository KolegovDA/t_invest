from decimal import Decimal

from strategy.grid_builder import GridBuilder


def main() -> None:
    builder = GridBuilder(levels_count=5)

    levels = builder.build_from_range(
        min_price=Decimal("250"),
        max_price=Decimal("300"),
    )

    for level in levels:
        print(level)


if __name__ == "__main__":
    main()
