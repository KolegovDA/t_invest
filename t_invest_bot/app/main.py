from decimal import Decimal

from broker.virtual_broker import VirtualBroker
from strategy.grid_engine import GridEngine, GridEngineConfig, GridLevel


levels = [
    GridLevel(index=1, price=Decimal("297.896175")),
]

config = GridEngineConfig(
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
    Decimal("299"),
    Decimal("298"),
    Decimal("297"),
    Decimal("297.20"),
    Decimal("297.45"),
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

broker.summary()
