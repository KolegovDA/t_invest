from config.settings import load_settings
from infrastructure.tinvest.client_factory import TInvestClientFactory
from infrastructure.tinvest.instrument_mapper import TInvestInstrumentMapper
from infrastructure.tinvest.instrument_provider import TInvestInstrumentProvider


def main() -> None:
    settings = load_settings()

    provider = TInvestInstrumentProvider(
        client_factory=TInvestClientFactory(settings.tinvest_token),
        mapper=TInvestInstrumentMapper(),
    )

    instrument = provider.find_share_by_ticker("SBER")

    if instrument is None:
        print("SBER not found")
        return

    print(instrument)


if __name__ == "__main__":
    main()
