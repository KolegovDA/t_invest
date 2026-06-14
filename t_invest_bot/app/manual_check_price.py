from config.settings import load_settings

from infrastructure.tinvest.client_factory import (
    TInvestClientFactory,
)
from infrastructure.tinvest.instrument_mapper import (
    TInvestInstrumentMapper,
)
from infrastructure.tinvest.instrument_provider import (
    TInvestInstrumentProvider,
)
from infrastructure.tinvest.last_price_provider import (
    TInvestLastPriceProvider,
)


def main() -> None:
    settings = load_settings()

    client_factory = TInvestClientFactory(
        settings.tinvest_token,
    )

    instrument_provider = TInvestInstrumentProvider(
        client_factory=client_factory,
        mapper=TInvestInstrumentMapper(),
    )

    price_provider = TInvestLastPriceProvider(
        client_factory=client_factory,
    )

    sber = instrument_provider.find_share_by_ticker(
        "SBER"
    )

    if sber is None:
        raise ValueError("SBER not found")

    price = price_provider.get_last_price(
        sber.id,
    )

    print("Instrument:", sber.ticker)
    print("Name:", sber.name)
    print("Price:", price)


if __name__ == "__main__":
    main()
