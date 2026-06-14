from dataclasses import dataclass

from t_tech.invest import InstrumentStatus

from domain.entities import Instrument
from infrastructure.tinvest.client_factory import TInvestClientFactory
from infrastructure.tinvest.instrument_mapper import TInvestInstrumentMapper


@dataclass(slots=True)
class TInvestInstrumentProvider:
    client_factory: TInvestClientFactory
    mapper: TInvestInstrumentMapper

    def get_shares(self) -> list[Instrument]:
        with self.client_factory.create_client() as client:
            response = client.instruments.shares(
                instrument_status=InstrumentStatus.INSTRUMENT_STATUS_BASE,
            )

        return [
            self.mapper.map_share(share)
            for share in response.instruments
        ]

    def find_share_by_ticker(
        self,
        ticker: str,
    ) -> Instrument | None:
        ticker = ticker.upper()

        for instrument in self.get_shares():
            if instrument.ticker.upper() == ticker:
                return instrument

        return None
