from decimal import Decimal

from application.sandbox_trading_session import SandboxTradingSession
from broker.live_order_manager import LiveOrderManager
from config.settings import load_settings
from infrastructure.tinvest.client_factory import TInvestClientFactory
from infrastructure.tinvest.instrument_mapper import TInvestInstrumentMapper
from infrastructure.tinvest.instrument_provider import TInvestInstrumentProvider
from infrastructure.tinvest.last_price_provider import TInvestLastPriceProvider
from infrastructure.tinvest.quotation_mapper import TInvestQuotationMapper
from infrastructure.tinvest.sandbox_account_provider import (
    TInvestSandboxAccountProvider,
)
from infrastructure.tinvest.sandbox_order_executor import (
    TInvestSandboxOrderExecutor,
)
from strategy.grid_engine import GridEngine, GridEngineConfig, GridLevel


def main() -> None:
    settings = load_settings()

    token = settings.tinvest_sandbox_token or settings.tinvest_token

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

    sandbox_account_provider = TInvestSandboxAccountProvider(
        client_factory=client_factory,
    )

    order_executor = TInvestSandboxOrderExecutor(
        client_factory=client_factory,
        quotation_mapper=TInvestQuotationMapper(),
    )

    instrument = instrument_provider.find_share_by_ticker("SBER")

    if instrument is None:
        raise ValueError("SBER not found")

    current_price = price_provider.get_last_price(
        instrument.id,
    )

    print("Instrument:", instrument)
    print("Current price:", current_price)

    sandbox_account_id = sandbox_account_provider.open_account()

    print("Sandbox account:", sandbox_account_id)

    balance = sandbox_account_provider.pay_in(
        account_id=sandbox_account_id,
        amount=Decimal("100000"),
    )

    print("Sandbox balance:", balance)

    grid = GridEngine(
        instrument_id=instrument.id,
        levels=[
            GridLevel(
                index=1,
                price=current_price * Decimal("1.01"),
            ),
        ],
        config=GridEngineConfig(
            quantity=1,
            entry_rebound_percent=Decimal("0.01"),
            entry_limit_offset_percent=Decimal("0.01"),
        ),
    )

    live_order_manager = LiveOrderManager(
        account_id=sandbox_account_id,
        order_executor=order_executor,
    )

    session = SandboxTradingSession(
        grid_engine=grid,
        live_order_manager=live_order_manager,
    )

    prices = [
        current_price,
        current_price * Decimal("0.995"),
        current_price * Decimal("0.990"),
        current_price * Decimal("0.992"),
        current_price * Decimal("0.995"),
    ]

    try:
        for price in prices:
            price = price.quantize(
                Decimal("0.01"),
            )

            placed_orders = session.on_price(
                price=price,
            )

            print("PRICE:", price)
            print("PLACED ORDERS:", placed_orders)

            if placed_orders:
                break

    finally:
        session.stop()

        print("All live orders canceled")

        sandbox_account_provider.close_account(
            account_id=sandbox_account_id,
        )

        print("Sandbox account closed")


if __name__ == "__main__":
    main()
