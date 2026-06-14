from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from infrastructure.tinvest.candles_mapper import TInvestCandlesMapper


@dataclass
class FakeQuotation:
    units: int
    nano: int


@dataclass
class FakeCandle:
    open: FakeQuotation
    high: FakeQuotation
    low: FakeQuotation
    close: FakeQuotation
    volume: int
    time: datetime


def test_tinvest_candles_mapper_maps_to_domain_candle() -> None:
    source = FakeCandle(
        open=FakeQuotation(units=100, nano=500000000),
        high=FakeQuotation(units=110, nano=0),
        low=FakeQuotation(units=95, nano=250000000),
        close=FakeQuotation(units=105, nano=750000000),
        volume=12345,
        time=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )

    mapper = TInvestCandlesMapper()

    candle = mapper.map_candle(
        instrument_id="SBER",
        source_candle=source,
    )

    assert candle.instrument_id == "SBER"
    assert candle.open == Decimal("100.5")
    assert candle.high == Decimal("110")
    assert candle.low == Decimal("95.25")
    assert candle.close == Decimal("105.75")
    assert candle.volume == 12345
    assert candle.timestamp == datetime(2024, 1, 1, tzinfo=timezone.utc)
