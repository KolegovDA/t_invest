from contextlib import nullcontext
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

from infrastructure.tinvest.candles_mapper import TInvestCandlesMapper
from infrastructure.tinvest.history_provider import TInvestHistoryProvider


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


@pytest.mark.parametrize("interval, days, window_days", [
    ("15m", 7, 1), ("1h", 30, 7), ("4h", 90, 30), ("1d", 365, 365),
])
def test_history_provider_batches_sorts_and_deduplicates_candles(
    interval: str, days: int, window_days: int,
) -> None:
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    finish = start + timedelta(days=days)
    calls = []

    def get_candles(**kwargs):
        calls.append(kwargs)
        assert kwargs["to"] - kwargs["from_"] <= timedelta(days=window_days)
        quotation = FakeQuotation(units=100, nano=0)
        return SimpleNamespace(candles=[
            FakeCandle(quotation, quotation, quotation, quotation, 1, time)
            for time in (kwargs["to"], kwargs["from_"])
        ])

    provider = TInvestHistoryProvider(
        client_factory=SimpleNamespace(create_client=lambda: nullcontext(
            SimpleNamespace(market_data=SimpleNamespace(get_candles=get_candles)),
        )),
        mapper=TInvestCandlesMapper(),
    )

    candles = provider.get_candles("SBER", start, finish, interval)

    assert len(calls) == (days + window_days - 1) // window_days
    assert calls[0]["from_"] == start
    assert calls[-1]["to"] == finish
    assert len(candles) == len(calls) + 1
    assert [candle.timestamp for candle in candles] == sorted({
        candle.timestamp for candle in candles
    })
    assert candles[0].timestamp == start
    assert candles[-1].timestamp == finish
