from datetime import datetime
from decimal import Decimal
from typing import Any

from domain.entities import Candle


class TInvestCandlesMapper:
    def map_candle(
        self,
        instrument_id: str,
        source_candle: Any,
    ) -> Candle:
        return Candle(
            instrument_id=instrument_id,
            open=self._quotation_to_decimal(source_candle.open),
            high=self._quotation_to_decimal(source_candle.high),
            low=self._quotation_to_decimal(source_candle.low),
            close=self._quotation_to_decimal(source_candle.close),
            volume=int(source_candle.volume),
            timestamp=self._extract_timestamp(source_candle),
        )

    def map_candles(
        self,
        instrument_id: str,
        source_candles: list[Any],
    ) -> list[Candle]:
        return [
            self.map_candle(
                instrument_id=instrument_id,
                source_candle=source_candle,
            )
            for source_candle in source_candles
        ]

    def _quotation_to_decimal(self, quotation: Any) -> Decimal:
        units = Decimal(str(getattr(quotation, "units", 0)))
        nano = Decimal(str(getattr(quotation, "nano", 0)))

        return units + nano / Decimal("1000000000")

    def _extract_timestamp(self, source_candle: Any) -> datetime:
        timestamp = getattr(source_candle, "time", None)

        if timestamp is None:
            raise ValueError("Candle timestamp is missing")

        return timestamp
