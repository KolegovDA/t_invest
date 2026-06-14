from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from domain.entities import Candle


@dataclass(slots=True)
class PriceRange:
    min_price: Decimal
    max_price: Decimal


@dataclass(slots=True)
class HistoryAnalyzer:
    exclude_first_days: int = 7

    def calculate_range(self, candles: list[Candle]) -> PriceRange:
        if not candles:
            raise ValueError("Candles list is empty")

        filtered_candles = self._exclude_first_days(candles)

        if not filtered_candles:
            raise ValueError("No candles left after excluding first days")

        min_price = min(candle.low for candle in filtered_candles)
        max_price = max(candle.high for candle in filtered_candles)

        if min_price <= Decimal("0"):
            raise ValueError("min_price must be greater than zero")

        if max_price <= min_price:
            raise ValueError("max_price must be greater than min_price")

        return PriceRange(
            min_price=min_price,
            max_price=max_price,
        )

    def _exclude_first_days(self, candles: list[Candle]) -> list[Candle]:
        sorted_candles = sorted(candles, key=lambda candle: candle.timestamp)

        first_timestamp = sorted_candles[0].timestamp
        cutoff_timestamp = first_timestamp + timedelta(days=self.exclude_first_days)

        return [
            candle
            for candle in sorted_candles
            if candle.timestamp >= cutoff_timestamp
        ]
