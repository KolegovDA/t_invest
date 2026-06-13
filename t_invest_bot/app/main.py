from decimal import Decimal

from strategy.grid_engine import GridEngine, GridLevel, GridEngineConfig


def main():
    grid = GridEngine(
        instrument_id="SBER",
        levels=[
            GridLevel(index=1, price=Decimal("300")),
        ],
        config=GridEngineConfig(
            quantity=10,
        ),
    )

    prices = [
        Decimal("305"),
        Decimal("302"),
        Decimal("300"),
        Decimal("299"),
        Decimal("298"),
        Decimal("297"),
        Decimal("297.20"),
        Decimal("297.45"),
    ]

    for price in prices:
        commands = grid.on_price(price)
        print(f"price={price}, commands={commands}")


if __name__ == "__main__":
    main()
