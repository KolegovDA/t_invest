from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
APP_DIR = ROOT / "app"

sys.path.insert(0, str(APP_DIR))

from decimal import Decimal

from broker.order_manager import OrderManager
from broker.virtual_broker import VirtualBroker
from strategy.grid_engine import GridEngine, GridEngineConfig, GridLevel


def process_price(
    price: Decimal,
    engine: GridEngine,
    order_manager: OrderManager,
) -> None:
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
        print("EVENT:", event)
        engine.on_trade_executed(event)


def run_scenario() -> None:
    instrument_id = "SBER"

    levels = [
        GridLevel(index=1, price=Decimal("300")),
        GridLevel(index=2, price=Decimal("296")),
        GridLevel(index=3, price=Decimal("292")),
        GridLevel(index=4, price=Decimal("288")),
        GridLevel(index=5, price=Decimal("284")),
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
        # First profitable cycle on level 1
        Decimal("305"),
        Decimal("300"),
        Decimal("298"),
        Decimal("296"),
        Decimal("294"),
        Decimal("292"),
        Decimal("290"),
        Decimal("288"),
        Decimal("286"),
        Decimal("284"),
        Decimal("282"),
        Decimal("280"),
        Decimal("280.50"),
        Decimal("286"),
        Decimal("292"),
        Decimal("298"),
        Decimal("304"),
        Decimal("302"),

        # Second profitable cycle on level 1/2
        Decimal("300"),
        Decimal("296"),
        Decimal("292"),
        Decimal("288"),
        Decimal("284"),
        Decimal("280"),
        Decimal("280.50"),
        Decimal("286"),
        Decimal("292"),
        Decimal("298"),
        Decimal("304"),
        Decimal("302"),

        # Deep fall to open several positions
        Decimal("300"),
        Decimal("296"),
        Decimal("292"),
        Decimal("288"),
        Decimal("284"),
        Decimal("280"),
        Decimal("276"),
        Decimal("272"),
        Decimal("268"),
        Decimal("264"),
        Decimal("260"),
        Decimal("260.50"),
        Decimal("259"),
        Decimal("259.50"),
        Decimal("258"),
        Decimal("258.50"),
        Decimal("257"),
        Decimal("257.50"),
        Decimal("256"),
        Decimal("256.50"),
        Decimal("256.20"),
    ]

    for price in prices:
        process_price(
            price=price,
            engine=engine,
            order_manager=order_manager,
        )

    print()
    print("=" * 60)
    broker.summary()
    print("=" * 60)

    print()
    print("ENGINE:")
    print("Open positions:", engine.open_positions)
    print("Realized profit:", engine.realized_profit)

    if len(engine.open_positions) >= 5:
        floating_loss = engine.risk_manager.calculate_floating_loss(
            open_positions=engine.open_positions,
            current_price=prices[-1],
        )
        print("Floating loss:", floating_loss)
        print("Required profit:", floating_loss * engine.config.compensation_multiplier)


if __name__ == "__main__":
    run_scenario()
