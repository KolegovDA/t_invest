from decimal import Decimal

from broker.order_manager import OrderManager
from broker.virtual_broker import VirtualBroker
from strategy.grid_engine import GridEngine, GridEngineConfig, GridLevel


def run_scenario() -> None:
    instrument_id = "SBER"

    levels = [
        GridLevel(index=1, price=Decimal("300")),
        GridLevel(index=2, price=Decimal("297")),
        GridLevel(index=3, price=Decimal("294")),
        GridLevel(index=4, price=Decimal("291")),
        GridLevel(index=5, price=Decimal("288")),
    ]

    engine = GridEngine(
        instrument_id=instrument_id,
        levels=levels,
        config=GridEngineConfig(
            quantity=10,
            min_open_positions_for_compensation=5,
            compensation_multiplier=Decimal("3"),
        ),
    )

    broker = VirtualBroker(
        cash=Decimal("100000"),
    )

    order_manager = OrderManager(
        broker=broker,
    )

    prices = [
        Decimal("305"),
        Decimal("302"),
        Decimal("300"),
        Decimal("299"),
        Decimal("297"),
        Decimal("296"),
        Decimal("294"),
        Decimal("293"),
        Decimal("291"),
        Decimal("290"),
        Decimal("288"),
        Decimal("287"),
        Decimal("289"),
        Decimal("291"),
        Decimal("293"),
        Decimal("296"),
        Decimal("299"),
        Decimal("302"),
        Decimal("305"),
        Decimal("300"),
        Decimal("295"),
        Decimal("290"),
        Decimal("285"),
    ]

    for price in prices:
        commands = engine.on_price(price)

        if commands:
            print()
            print(f"PRICE={price}")
            print("COMMANDS:")
            for command in commands:
                print(command)

        order_manager.add_commands(commands)

        events = order_manager.process_price(price)

        for event in events:
            engine.on_trade_executed(event)

    print()
    print("=" * 60)
    broker.summary()
    print("=" * 60)


if __name__ == "__main__":
    run_scenario()
