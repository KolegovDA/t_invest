from decimal import Decimal

from application.multi_instrument_session_config import (
    InstrumentConfig,
    MultiInstrumentSessionConfig,
)


def test_multi_config_contains_instruments() -> None:
    config = MultiInstrumentSessionConfig(
        instruments=[
            InstrumentConfig(
                ticker="SBER",
                levels_count=20,
                quantity=10,
            ),
            InstrumentConfig(
                ticker="GAZP",
                levels_count=15,
                quantity=5,
            ),
        ]
    )

    assert len(config.instruments) == 2
    assert config.instruments[0].ticker == "SBER"
    assert config.instruments[1].ticker == "GAZP"


def test_instrument_config_converts_to_grid_engine_config() -> None:
    instrument_config = InstrumentConfig(
        ticker="SBER",
        levels_count=20,
        quantity=10,
        entry_rebound_percent=Decimal("0.10"),
        entry_limit_offset_percent=Decimal("0.20"),
        exit_limit_offset_percent=Decimal("0.30"),
        trailing_percent=Decimal("0.40"),
        min_profit_percent=Decimal("0.50"),
        take_profit_buffer_percent=Decimal("0.60"),
        min_open_positions_for_compensation=4,
        compensation_multiplier=Decimal("2"),
    )

    grid_config = instrument_config.to_grid_engine_config()

    assert grid_config.quantity == 10
    assert grid_config.entry_rebound_percent == Decimal("0.10")
    assert grid_config.entry_limit_offset_percent == Decimal("0.20")
    assert grid_config.exit_limit_offset_percent == Decimal("0.30")
    assert grid_config.trailing_percent == Decimal("0.40")
    assert grid_config.min_profit_percent == Decimal("0.50")
    assert grid_config.take_profit_buffer_percent == Decimal("0.60")
    assert grid_config.min_open_positions_for_compensation == 4
    assert grid_config.compensation_multiplier == Decimal("2")
