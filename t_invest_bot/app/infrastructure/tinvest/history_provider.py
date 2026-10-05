from dataclasses import dataclass
from datetime import datetime, timedelta

from t_tech.invest import CandleInterval

from domain.entities import Candle
from infrastructure.tinvest.candles_mapper import TInvestCandlesMapper
from infrastructure.tinvest.client_factory import TInvestClientFactory


CANDLE_INTERVALS: dict[
    str,
    CandleInterval,
] = {
    "15m": (
        CandleInterval
        .CANDLE_INTERVAL_15_MIN
    ),

    "1h": (
        CandleInterval
        .CANDLE_INTERVAL_HOUR
    ),

    "4h": (
        CandleInterval
        .CANDLE_INTERVAL_4_HOUR
    ),

    "1d": (
        CandleInterval
        .CANDLE_INTERVAL_DAY
    ),
}


@dataclass(slots=True)
class TInvestHistoryProvider:
    client_factory: TInvestClientFactory
    mapper: TInvestCandlesMapper

    def get_daily_candles(
        self,
        instrument_id: str,
        date_from: datetime,
        date_to: datetime,
    ) -> list[Candle]:
        with self.client_factory.create_client() as client:
            response = client.market_data.get_candles(
                instrument_id=instrument_id,
                from_=date_from,
                to=date_to,
                interval=CandleInterval.CANDLE_INTERVAL_DAY,
            )

        return self.mapper.map_candles(
            instrument_id=instrument_id,
            source_candles=list(response.candles),
        )

    def get_candles(
        self,
        instrument_id: str,
        date_from: datetime,
        date_to: datetime,
        interval: str,
    ) -> list[Candle]:
        candle_interval = (
            CANDLE_INTERVALS
            .get(
                interval,
            )
        )

        if (
            candle_interval
            is None
        ):
            raise ValueError(
                "Unsupported interval: "
                f"{interval}"
            )

        if date_from >= date_to:
            return []
        window = {
            "15m": timedelta(days=1),
            "1h": timedelta(days=7),
            "4h": timedelta(days=30),
            "1d": timedelta(days=365),
        }[interval]
        candles_by_time = {}
        with self.client_factory.create_client() as client:
            start = date_from
            while start < date_to:
                end = min(start + window, date_to)
                response = client.market_data.get_candles(
                    instrument_id=instrument_id,
                    from_=start,
                    to=end,
                    interval=candle_interval,
                )
                for candle in self.mapper.map_candles(
                    instrument_id=instrument_id,
                    source_candles=list(response.candles),
                ):
                    if date_from <= candle.timestamp <= date_to:
                        candles_by_time[candle.timestamp] = candle
                start = end

        return [candles_by_time[time] for time in sorted(candles_by_time)]
