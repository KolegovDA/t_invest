from decimal import Decimal

from broker.order_manager import OrderManager
from broker.virtual_broker import VirtualBroker, VirtualLevelPosition
from domain.positions import OpenLevelPosition
from portfolio.portfolio_manager import PortfolioManager
from strategy.grid_engine import GridEngine, GridEngineConfig, GridLevel


def main() -> None:
    instrument_id = "SBER"

    levels = [
        GridLevel(index=1, price=Decimal("300")),
        GridLevel(index=2, price=Decimal("298")),
        GridLevel(index=3, price=Decimal("296")),
        GridLevel(index=4, price=Decimal("294")),
        GridLevel(index=5, price=Decimal("292")),
    ]

    config = GridEngineConfig(
        entry_limit_offset_percent=Decimal("0.15"),
        exit_limit_offset_percent=Decimal("0.15"),
        entry_rebound_percent=Decimal("0.15"),
        trailing_percent=Decimal("0.50"),
        min_profit_percent=Decimal("0.30"),
        take_profit_buffer_percent=Decimal("0.15"),
        fallback_buy_commission_percent=Decimal("0.30"),
        fallback_sell_commission_percent=Decimal("0.30"),
        min_open_positions_for_compensation=5,
        compensation_multiplier=Decimal("3"),
        quantity=10,
    )

    engine = GridEngine(
        instrument_id=instrument_id,
        levels=levels,
        config=config,
    )

    broker = VirtualBroker(cash=Decimal("100000"))
    order_manager = OrderManager(broker=broker)
    portfolio_manager = PortfolioManager(broker=broker)

    seeded_positions = {
        1: OpenLevelPosition(
            level_index=1,
            entry_price=Decimal("300"),
            quantity=10,
            buy_commission=Decimal("9"),
            expected_sell_commission_percent=Decimal("0.30"),
            hard_take_profit_price=Decimal("303.15"),
        ),
        2: OpenLevelPosition(
            level_index=2,
            entry_price=Decimal("298"),
            quantity=10,
            buy_commission=Decimal("8.94"),
            expected_sell_commission_percent=Decimal("0.30"),
            hard_take_profit_price=Decimal("301.13"),
        ),
        3: OpenLevelPosition(
            level_index=3,
            entry_price=Decimal("296"),
            quantity=10,
            buy_commission=Decimal("8.88"),
            expected_sell_commission_percent=Decimal("0.30"),
            hard_take_profit_price=Decimal("299.11"),
        ),
        4: OpenLevelPosition(
            level_index=4,
            entry_price=Decimal("294"),
            quantity=10,
            buy_commission=Decimal("8.82"),
            expected_sell_commission_percent=Decimal("0.30"),
            hard_take_profit_price=Decimal("297.09"),
        ),
        5: OpenLevelPosition(
            level_index=5,
            entry_price=Decimal("292"),
            quantity=10,
            buy_commission=Decimal("8.76"),
            expected_sell_commission_percent=Decimal("0.30"),
            hard_take_profit_price=Decimal("295.07"),
        ),
    }

    engine.open_positions = seeded_positions
    engine.realized_profit = Decimal("1033.20")

    broker.level_positions = {
        ("SBER", 1): VirtualLevelPosition(
            instrument_id="SBER",
            level_index=1,
            quantity=10,
            entry_price=Decimal("300"),
            buy_commission=Decimal("9"),
        ),
        ("SBER", 2): VirtualLevelPosition(
            instrument_id="SBER",
            level_index=2,
            quantity=10,
            entry_price=Decimal("298"),
            buy_commission=Decimal("8.94"),
        ),
        ("SBER", 3): VirtualLevelPosition(
            instrument_id="SBER",
            level_index=3,
            quantity=10,
            entry_price=Decimal("296"),
            buy_commission=Decimal("8.88"),
        ),
        ("SBER", 4): VirtualLevelPosition(
            instrument_id="SBER",
            level_index=4,
            quantity=10,
            entry_price=Decimal("294"),
            buy_commission=Decimal("8.82"),
        ),
        ("SBER", 5): VirtualLevelPosition(
            instrument_id="SBER",
            level_index=5,
            quantity=10,
            entry_price=Decimal("292"),
            buy_commission=Decimal("8.76"),
        ),
    }

    current_price = Decimal("290")

    commands = engine.on_price(current_price)
    order_manager.add_commands(commands)

    print("Commands:")
    for command in commands:
        print(command)

    events = order_manager.process_price(current_price)

    print()
    print("Events:")
    for event in events:
        print(event)
        engine.on_trade_executed(event)

    print()
    broker.summary()

    print()
    portfolio_manager.summary()

    print()
    print("Engine open positions:", engine.open_positions)
    print("Engine realized profit:", engine.realized_profit)


if __name__ == "__main__":
    main()
