from decimal import Decimal

from broker.virtual_broker import VirtualBroker
from domain.commands import TradingCommand
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

pending_commands: list[TradingCommand] = []

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

    Decimal("299"),
    Decimal("298"),
    Decimal("297"),
    Decimal("297.30"),
    Decimal("297.60"),
    Decimal("298"),
    Decimal("299"),
    Decimal("301"),
    Decimal("302"),
]

for price in prices:
    new_commands = engine.on_price(price)
    pending_commands.extend(new_commands)

    print(f"price={price}, new_commands={new_commands}")
    print(f"pending_commands={pending_commands}")

    events = broker.execute_commands(
        commands=pending_commands,
        current_price=price,
    )

    for event in events:
        pending_commands = [
            command
            for command in pending_commands
            if command.price != event.price
        ]

        next_commands = engine.on_trade_executed(event)
        pending_commands.extend(next_commands)

        print(f"event={event}")
        print(f"next_commands={next_commands}")

broker.summary()
