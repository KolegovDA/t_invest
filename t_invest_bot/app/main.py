from decimal import Decimal

from broker.virtual_broker import VirtualBroker
from strategy.grid_engine import GridEngine, GridLevel, GridEngineConfig


def main():
    instrument_id = "SBER"

    levels = [
        GridLevel(index=1, price=Decimal("297.50")),
        GridLevel(index=2, price=Decimal("295.00")),
        GridLevel(index=3, price=Decimal("292.50")),
    ]

    config = GridEngineConfig(
        entry_limit_offset_percent=Decimal("0.15"),
        entry_rebound_percent=Decimal("0.15"),
        trailing_percent=Decimal("0.50"),
        take_profit_percent=Decimal("1.00"),
        quantity=10,
    )

    engine = GridEngine(
        instrument_id=instrument_id,
        levels=levels,
        config=config,
    )

    broker = VirtualBroker(cash=Decimal("100000"))

    prices = [
        Decimal("305"),
        Decimal("301"),
        Decimal("298"),

        Decimal("297.50"),
        Decimal("297.00"),
        Decimal("297.20"),
        Decimal("297.45"),

        Decimal("296"),
        Decimal("295.00"),
        Decimal("294.70"),
        Decimal("295.00"),
        Decimal("295.20"),

        Decimal("293"),
        Decimal("292.50"),
        Decimal("292.20"),
        Decimal("292.50"),
        Decimal("292.70"),

        Decimal("296.50"),
        Decimal("299.00"),
        Decimal("301.00"),
    ]

    active_commands = []

    for price in prices:
        commands = engine.on_price(price)

        active_commands.extend(commands)

        print(f"price={price}, new_commands={commands}")
        print(f"active_commands={active_commands}")

        events = broker.execute_commands(
            commands=active_commands,
            current_price=price,
        )

        executed_commands = []

        for event in events:
            for command in active_commands:
                if (
                    command.instrument_id == event.instrument_id
                    and command.level_index == event.level_index
                    and command.quantity == event.quantity
                    and command.price == event.price
                ):
                    executed_commands.append(command)
                    break

            next_commands = engine.on_trade_executed(event)
            active_commands.extend(next_commands)

            print(f"event={event}, next_commands={next_commands}")

        for command in executed_commands:
            if command in active_commands:
                active_commands.remove(command)

        print()
        broker.summary()


if __name__ == "__main__":
    main()
