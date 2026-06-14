from decimal import Decimal

from broker.order_manager import OrderManager
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
    order_manager = OrderManager(broker=broker)

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

    for price in prices:
        new_commands = engine.on_price(price)
        order_manager.add_commands(new_commands)

        events = order_manager.process_price(price)

        for event in events:
            next_commands = engine.on_trade_executed(event)
            order_manager.add_commands(next_commands)

        print(f"price={price}")
        print(f"new_commands={new_commands}")
        print(f"events={events}")
        print(f"active_commands={order_manager.active_commands}")
        print()

    broker.summary()


if __name__ == "__main__":
    main()
