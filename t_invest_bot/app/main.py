from decimal import Decimal

from strategy.grid_engine import GridEngine, GridLevel, GridEngineConfig
from broker.virtual_broker import VirtualBroker


levels = [
    GridLevel(price=Decimal("297.896175"), quantity=10),
]

config = GridEngineConfig(
    instrument_id="SBER",
    levels=levels,
)

engine = GridEngine(config=config)

broker = VirtualBroker(
    cash=Decimal("100000")
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

    broker.execute_commands(
        commands=commands,
        current_price=price,
    )

broker.summary()
