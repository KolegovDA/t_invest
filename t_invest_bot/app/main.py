from decimal import Decimal

from broker.virtual_broker import VirtualBroker
from portfolio.portfolio_manager import PortfolioManager
from risk.risk_manager import RiskManager, RiskManagerConfig
from strategy.grid_engine import GridEngine, GridLevel, GridEngineConfig


def process_instrument_price(
    instrument_id: str,
    price: Decimal,
    engine: GridEngine,
    broker: VirtualBroker,
    portfolio_manager: PortfolioManager,
    risk_manager: RiskManager,
    active_commands: list,
) -> None:
    portfolio_manager.update_price(instrument_id, price)

    commands = engine.on_price(price)
    approved_commands = risk_manager.filter_commands(commands)

    active_commands.extend(approved_commands)

    print(f"[{instrument_id}] price={price}, new_commands={commands}")
    print(f"[{instrument_id}] approved_commands={approved_commands}")
    print(f"[{instrument_id}] active_commands={active_commands}")

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
        approved_next_commands = risk_manager.filter_commands(next_commands)

        active_commands.extend(approved_next_commands)

        print(
            f"[{instrument_id}] event={event}, "
            f"next_commands={next_commands}, "
            f"approved_next_commands={approved_next_commands}"
        )

    for command in executed_commands:
        if command in active_commands:
            active_commands.remove(command)

    print()


def main() -> None:
    broker = VirtualBroker(cash=Decimal("100000"))
    portfolio_manager = PortfolioManager(broker=broker)

    risk_manager = RiskManager(
        broker=broker,
        config=RiskManagerConfig(
            max_position_value_per_instrument=Decimal("5000"),
            max_total_position_value=Decimal("15000"),
        ),
    )

    config = GridEngineConfig(
        entry_limit_offset_percent=Decimal("0.15"),
        entry_rebound_percent=Decimal("0.15"),
        trailing_percent=Decimal("0.50"),
        take_profit_percent=Decimal("1.00"),
        quantity=10,
    )

    engines = {
        "SBER": GridEngine(
            instrument_id="SBER",
            levels=[
                GridLevel(index=1, price=Decimal("297.50")),
                GridLevel(index=2, price=Decimal("295.00")),
                GridLevel(index=3, price=Decimal("292.50")),
            ],
            config=config,
        ),
        "GAZP": GridEngine(
            instrument_id="GAZP",
            levels=[
                GridLevel(index=1, price=Decimal("162.00")),
                GridLevel(index=2, price=Decimal("160.00")),
                GridLevel(index=3, price=Decimal("158.00")),
            ],
            config=config,
        ),
    }

    price_stream = [
        ("SBER", Decimal("305")),
        ("GAZP", Decimal("166")),
        ("SBER", Decimal("301")),
        ("GAZP", Decimal("163")),
        ("SBER", Decimal("298")),
        ("GAZP", Decimal("162.00")),
        ("SBER", Decimal("297.50")),
        ("GAZP", Decimal("161.70")),
        ("SBER", Decimal("297.00")),
        ("GAZP", Decimal("161.90")),
        ("SBER", Decimal("297.20")),
        ("GAZP", Decimal("162.10")),
        ("SBER", Decimal("297.45")),
        ("GAZP", Decimal("160.00")),
        ("SBER", Decimal("296")),
        ("GAZP", Decimal("159.70")),
        ("SBER", Decimal("295.00")),
        ("GAZP", Decimal("160.00")),
        ("SBER", Decimal("294.70")),
        ("GAZP", Decimal("160.20")),
        ("SBER", Decimal("295.00")),
        ("GAZP", Decimal("158.00")),
        ("SBER", Decimal("295.20")),
        ("GAZP", Decimal("157.70")),
        ("SBER", Decimal("293")),
        ("GAZP", Decimal("158.00")),
        ("SBER", Decimal("292.50")),
        ("GAZP", Decimal("158.20")),
        ("SBER", Decimal("292.20")),
        ("GAZP", Decimal("163.50")),
        ("SBER", Decimal("292.50")),
        ("SBER", Decimal("292.70")),
        ("SBER", Decimal("296.50")),
        ("SBER", Decimal("299.00")),
        ("SBER", Decimal("301.00")),
    ]

    active_commands_by_instrument = {
        "SBER": [],
        "GAZP": [],
    }

    for instrument_id, price in price_stream:
        process_instrument_price(
            instrument_id=instrument_id,
            price=price,
            engine=engines[instrument_id],
            broker=broker,
            portfolio_manager=portfolio_manager,
            risk_manager=risk_manager,
            active_commands=active_commands_by_instrument[instrument_id],
        )

    broker.summary()
    portfolio_manager.summary()


if __name__ == "__main__":
    main()
