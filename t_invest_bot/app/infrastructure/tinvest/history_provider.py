from dataclasses import dataclass
from datetime import datetime

from tinkoff.invest import CandleInterval, Client

from domain.entities import Candle
from infrastructure.tinvest.candles_mapper import TInvestCandlesMapper


@dataclass(slots=True)
class TInvestHistoryProvider:
    token: str
    mapper: TInvestCandlesMapper

    def get_daily_candles(
        self,
        instrument_id: str,
        figi: str,
        date_from: datetime,
        date_to: datetime,
    ) -> list[Candle]:
        with Client(self.token) as client:
            source_candles = client.market_data.get_candles(
                figi=figi,
                from_=date_from,
                to=date_to,
                interval=CandleInterval.CANDLE_INTERVAL_DAY,
            ).candles

        return self.mapper.map_candles(
            instrument_id=instrument_id,
            source_candles=list(source_candles),
        )
