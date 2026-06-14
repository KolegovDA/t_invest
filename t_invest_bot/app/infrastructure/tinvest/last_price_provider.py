from dataclasses import dataclass
from decimal import Decimal

from infrastructure.tinvest.client_factory import TInvestClientFactory


@dataclass(slots=True)
class TInvestLastPriceProvider:
    client_factory: TInvestClientFactory

    def get_last_price(
        self,
        instrument_uid: str,
    ) -> Decimal:
        with self.client_factory.create_client() as client:
            response = client.market_data.get_last_prices(
                instrument_id=[
                    instrument_uid,
                ],
            )

        if not response.last_prices:
            raise ValueError(
                f"Price not found for {instrument_uid}"
            )

        quotation = response.last_prices[0].price

        return (
            Decimal(str(quotation.units))
            + Decimal(str(quotation.nano))
            / Decimal("1000000000")
        )
