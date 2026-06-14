from config.settings import load_settings
from infrastructure.tinvest.client_factory import TInvestClientFactory
from infrastructure.tinvest.instrument_mapper import TInvestInstrumentMapper
from infrastructure.tinvest.instrument_provider import TInvestInstrumentProvider
from infrastructure.tinvest.last_price_provider import TInvestLastPriceProvider
from portfolio.capital_validator import CapitalValidator


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

    instrument = instrument_provider.find_share_by_ticker("SBER")

    if instrument is None:
        raise ValueError("SBER not found")

    price = price_provider.get_last_price(
        instrument.id,
    )

    validator = CapitalValidator()

    requirement = validator.calculate_required_deposit(
        instrument=instrument,
        last_price=price,
        levels_count=20,
    )

    print("Instrument:", instrument.ticker)
    print("Name:", instrument.name)
    print("Lot size:", instrument.lot_size)
    print("Price:", price)
    print("Levels:", requirement.levels_count)
    print("Min order amount:", requirement.min_order_amount)
    print("Order amount:", requirement.order_amount)
    print("Required deposit:", requirement.required_deposit)


if __name__ == "__main__":
    main()
