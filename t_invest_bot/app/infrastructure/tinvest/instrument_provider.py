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
                instrument_status=(
                    InstrumentStatus
                    .INSTRUMENT_STATUS_BASE
                ),
            )

        return [
            self.mapper.map_share(share)
            for share
            in response.instruments
            if getattr(
                share,
                "api_trade_available_flag",
                True,
            )
        ]

    def find_share_by_ticker(
        self,
        ticker: str,
    ) -> Instrument | None:
        normalized_ticker = (
            ticker
            .strip()
            .upper()
        )

        for instrument in self.get_shares():
            if (
                instrument.ticker.upper()
                == normalized_ticker
            ):
                return instrument

        return None

    def search_shares(
        self,
        query: str,
        limit: int = 50,
    ) -> list[Instrument]:
        normalized_query = (
            query
            .strip()
            .casefold()
        )

        safe_limit = max(
            1,
            min(
                int(limit),
                100,
            ),
        )

        shares = self.get_shares()

        if not normalized_query:
            matches = shares
        else:
            matches = [
                instrument
                for instrument
                in shares
                if (
                    normalized_query
                    in instrument.ticker.casefold()
                    or normalized_query
                    in instrument.name.casefold()
                )
            ]

        matches.sort(
            key=lambda instrument: (
                0
                if instrument.ticker.casefold()
                == normalized_query
                else 1,
                0
                if instrument.ticker.casefold()
                .startswith(
                    normalized_query
                )
                else 1,
                instrument.ticker,
                instrument.name,
            )
        )

        return matches[:safe_limit]
