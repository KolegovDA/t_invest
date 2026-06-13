from decimal import Decimal

from broker.virtual_broker import VirtualBroker
from strategy.grid_engine import GridEngine, GridEngineConfig, GridLevel


levels = [
    GridLevel(index=1, price=Decimal("297.896175")),
]

config = GridEngineConfig(
    quantity=10,
    take_profit_percent=Decimal("1.00"),
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
    Decimal("299"),
    Decimal("298"),
    Decimal("297"),
    Decimal("297.20"),
    Decimal("297.45"),
    Decimal("298"),
    Decimal("299"),
    Decimal("300"),
    Decimal("301"),
]

for price in prices:
    commands = engine.on_price(price)
    print(f"price={price}, commands={commands}")

    events = broker.execute_commands(
        commands=commands,
        current_price=price,
    )

    if events:
        print(f"events={events}")

    for event in events:
        next_commands = engine.on_trade_executed(event)
        print(f"next_commands={next_commands}")

        next_events = broker.execute_commands(
            commands=next_commands,
            current_price=price,
        )

        if next_events:
            print(f"next_events={next_events}")

broker.summary()
