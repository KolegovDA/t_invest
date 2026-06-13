from decimal import Decimal

from strategy.grid_engine import GridEngine, GridLevel, GridEngineConfig
from broker.virtual_broker import VirtualBroker


def main():
    instrument_id = "SBER"

    levels = [
        GridLevel(
            instrument_id=instrument_id,
            level_index=1,
            buy_price=Decimal("297.50"),
            sell_price=Decimal("300.50"),
            quantity=10,
        ),
        GridLevel(
            instrument_id=instrument_id,
            level_index=2,
            buy_price=Decimal("295.00"),
            sell_price=Decimal("298.00"),
            quantity=10,
        ),
        GridLevel(
            instrument_id=instrument_id,
            level_index=3,
            buy_price=Decimal("292.50"),
            sell_price=Decimal("295.50"),
            quantity=10,
        ),
    ]

    config = GridEngineConfig(
        instrument_id=instrument_id,
        levels=levels,
    )

    engine = GridEngine(config)
    broker = VirtualBroker(start_cash=Decimal("100000"))

    prices = [
        Decimal("305"),
        Decimal("301"),
        Decimal("298"),
        Decimal("297.50"),  # BUY level 1
        Decimal("296"),
        Decimal("295.00"),  # BUY level 2
        Decimal("293"),
        Decimal("292.50"),  # BUY level 3
        Decimal("295.50"),  # SELL level 3
        Decimal("298.00"),  # SELL level 2
        Decimal("300.50"),  # SELL level 1
    ]

    for price in prices:
        commands = engine.on_price(price)

        print(f"price={price}, commands={commands}")

        for command in commands:
            broker.execute(command)

    print()
    broker.print_report()


if __name__ == "__main__":
    main()
