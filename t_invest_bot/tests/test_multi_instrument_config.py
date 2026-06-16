from application.multi_instrument_session_config import (
    InstrumentConfig,
    MultiInstrumentSessionConfig,
)


def test_multi_config_contains_instruments():
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
