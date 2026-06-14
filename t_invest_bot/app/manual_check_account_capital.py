from config.settings import load_settings
from infrastructure.tinvest.account_provider import TInvestAccountProvider
from infrastructure.tinvest.client_factory import TInvestClientFactory
from infrastructure.tinvest.instrument_mapper import TInvestInstrumentMapper
from infrastructure.tinvest.instrument_provider import TInvestInstrumentProvider
from infrastructure.tinvest.last_price_provider import TInvestLastPriceProvider
from portfolio.capital_validator import CapitalValidator


def select_account_id(
    settings_account_id: str | None,
    account_provider: TInvestAccountProvider,
) -> str:
    accounts = account_provider.get_accounts()

    if not accounts:
        raise ValueError("Accounts not found")

    if settings_account_id:
        for account in accounts:
            if account.id == settings_account_id:
                return account.id

        raise ValueError(
            f"TINVEST_ACCOUNT_ID={settings_account_id} not found"
        )

    print("TINVEST_ACCOUNT_ID is not set. Using first account.")
    print("Available accounts:")

    for account in accounts:
        print(account.id, account.name)

    return accounts[0].id


def main() -> None:
    settings = load_settings()

    client_factory = TInvestClientFactory(
        settings.tinvest_token,
    )

    account_provider = TInvestAccountProvider(
        client_factory=client_factory,
    )

    instrument_provider = TInvestInstrumentProvider(
        client_factory=client_factory,
        mapper=TInvestInstrumentMapper(),
    )

    price_provider = TInvestLastPriceProvider(
        client_factory=client_factory,
    )

    account_id = select_account_id(
        settings_account_id=settings.tinvest_account_id,
        account_provider=account_provider,
    )

    balance = account_provider.get_rub_balance(
        account_id=account_id,
    )

    instrument = instrument_provider.find_share_by_ticker("SBER")

    if instrument is None:
        raise ValueError("SBER not found")

    price = price_provider.get_last_price(
        instrument.id,
    )

    requirement = CapitalValidator().calculate_required_deposit(
        instrument=instrument,
        last_price=price,
        levels_count=20,
    )

    print("Account ID:", account_id)
    print("RUB balance:", balance.amount)
    print("Instrument:", instrument.ticker)
    print("Price:", price)
    print("Required deposit:", requirement.required_deposit)
    print(
        "Can start:",
        balance.amount >= requirement.required_deposit,
    )


if __name__ == "__main__":
    main()
