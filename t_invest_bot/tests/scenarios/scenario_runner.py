from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
APP_DIR = ROOT / "app"

sys.path.insert(0, str(APP_DIR))

from datetime import datetime, timedelta
from decimal import Decimal

from broker.order_manager import OrderManager
from broker.virtual_broker import VirtualBroker
from domain.entities import Candle
from strategy.grid_engine import GridEngineConfig
from strategy.grid_factory import GridFactory
from strategy.history_analyzer import HistoryAnalyzer


def process_price(
    price: Decimal,
    engine,
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


def build_test_history(instrument_id: str) -> list[Candle]:
    history_start = datetime(2024, 1, 1)

    candles: list[Candle] = []

    for i in range(20):
        candles.append(
            Candle(
                instrument_id=instrument_id,
                open=Decimal("290"),
                high=Decimal("310"),
                low=Decimal("280"),
                close=Decimal("290"),
                volume=1000,
                timestamp=history_start + timedelta(days=i),
            )
        )

    return candles


def run_scenario() -> None:
    instrument_id = "SBER"

    candles = build_test_history(
        instrument_id=instrument_id,
    )

    factory = GridFactory(
        history_analyzer=HistoryAnalyzer(exclude_first_days=7),
    )

    factory_result = factory.create_grid_engine(
        instrument_id=instrument_id,
        candles=candles,
        levels_count=5,
        config=GridEngineConfig(
            quantity=10,
            min_open_positions_for_compensation=5,
            compensation_multiplier=Decimal("3"),
        ),
    )

    engine = factory_result.grid_engine

    print("PRICE RANGE:", factory_result.price_range)
    print("LEVELS:")
    for level in engine.levels:
        print(level)

    broker = VirtualBroker(
        cash=Decimal("100000"),
    )

    order_manager = OrderManager(
        broker=broker,
    )

    prices = [
        # First profitable cycle
        Decimal("305"),
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

        # Second profitable cycle
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

    if engine.open_positions:
        floating_loss = engine.risk_manager.calculate_floating_loss(
            open_positions=engine.open_positions,
            current_price=prices[-1],
        )
        print("Floating loss:", floating_loss)
        print("Required profit:", floating_loss * engine.config.compensation_multiplier)


if __name__ == "__main__":
    run_scenario()
