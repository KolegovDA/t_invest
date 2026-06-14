from decimal import Decimal

from config.settings import load_settings
from infrastructure.tinvest.client_factory import TInvestClientFactory
from infrastructure.tinvest.instrument_mapper import TInvestInstrumentMapper
from infrastructure.tinvest.instrument_provider import (
    TInvestInstrumentProvider,
)
from infrastructure.tinvest.last_price_provider import (
    TInvestLastPriceProvider,
)
from infrastructure.tinvest.quotation_mapper import (
    TInvestQuotationMapper,
)
from infrastructure.tinvest.sandbox_account_provider import (
    TInvestSandboxAccountProvider,
)
from infrastructure.tinvest.sandbox_order_executor import (
    TInvestSandboxOrderExecutor,
)


def main() -> None:
    settings = load_settings()

    token = (
        settings.tinvest_sandbox_token
        or settings.tinvest_token
    )

    if not token:
        raise ValueError(
            "Sandbox token is not configured"
        )

    client_factory = TInvestClientFactory(
        token=token,
    )

    instrument_provider = TInvestInstrumentProvider(
        client_factory=client_factory,
        mapper=TInvestInstrumentMapper(),
    )

    price_provider = TInvestLastPriceProvider(
        client_factory=client_factory,
    )

    sandbox_account_provider = (
        TInvestSandboxAccountProvider(
            client_factory=client_factory,
        )
    )

    order_executor = TInvestSandboxOrderExecutor(
        client_factory=client_factory,
        quotation_mapper=TInvestQuotationMapper(),
    )

    instrument = (
        instrument_provider.find_share_by_ticker(
            "SBER"
        )
    )

    if instrument is None:
        raise ValueError(
            "SBER not found"
        )

    current_price = (
        price_provider.get_last_price(
            instrument.id,
        )
    )

    sandbox_account_id = (
        sandbox_account_provider.open_account()
    )

    print(
        f"Sandbox account: "
        f"{sandbox_account_id}"
    )

    balance = sandbox_account_provider.pay_in(
        account_id=sandbox_account_id,
        amount=Decimal("100000"),
    )

    print(
        f"Sandbox balance: {balance}"
    )

    print(
        f"SBER price: {current_price}"
    )

    limit_price = (
        current_price * Decimal("0.50")
    ).quantize(
        Decimal("0.01")
    )

    placed_order = (
        order_executor.place_limit_buy(
            account_id=sandbox_account_id,
            instrument_id=instrument.id,
            quantity=1,
            price=limit_price,
        )
    )

    print(
        f"Placed order: {placed_order}"
    )

    order_executor.cancel_order(
        account_id=sandbox_account_id,
        order_id=placed_order.order_id,
    )

    print(
        "Order canceled"
    )

    sandbox_account_provider.close_account(
        account_id=sandbox_account_id,
    )

    print(
        "Sandbox account closed"
    )


if __name__ == "__main__":
    main()
