from decimal import Decimal

from broker.virtual_broker import VirtualBroker
from strategy.grid_engine import GridEngine, GridLevel, GridEngineConfig


def main():
    levels = [
        GridLevel(index=1, price=Decimal("297.896175")),
        GridLevel(index=2, price=Decimal("295.000000")),
        GridLevel(index=3, price=Decimal("292.500000")),
    ]

    config = GridEngineConfig(
        entry_limit_offset_percent=Decimal("0.15"),
        entry_rebound_percent=Decimal("0.15"),
        trailing_percent=Decimal("0.50"),
        quantity=10,
    )

    engine = GridEngine(
        instrument_id="SBER",
        levels=levels,
        config=config,
    )

    broker = VirtualBroker(
        cash=Decimal("100000"),
    )

    prices = [
        Decimal("305"),
        Decimal("302"),
        Decimal("300"),
        Decimal("298"),
        Decimal("297"),
        Decimal("297.20"),
        Decimal("297.45"),

        Decimal("296"),
        Decimal("295"),
        Decimal("295.20"),
        Decimal("295.45"),

        Decimal("293"),
        Decimal("292.50"),
        Decimal("292.70"),
        Decimal("293.00"),

 
        Decimal("296.40"), 
        Decimal("298.90"),  
        Decimal("300.90"), 
    ]

    for price in prices:
        commands = engine.on_price(price)

        events = broker.execute_commands(
            commands=commands,
            current_price=price,
        )

        for event in events:
            next_commands = engine.on_trade_executed(event)

            next_events = broker.execute_commands(
                commands=next_commands,
                current_price=price,
            )

            for next_event in next_events:
                engine.on_trade_executed(next_event)

        print(f"price={price}, commands={commands}")

    broker.summary()


if __name__ == "__main__":
    main()
