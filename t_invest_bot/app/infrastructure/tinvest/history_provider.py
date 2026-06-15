from dataclasses import dataclass
from datetime import datetime

from t_tech.invest import CandleInterval

from domain.entities import Candle
from infrastructure.tinvest.candles_mapper import TInvestCandlesMapper
from infrastructure.tinvest.client_factory import TInvestClientFactory


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
