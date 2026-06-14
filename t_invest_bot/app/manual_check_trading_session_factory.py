from decimal import Decimal

from application.trading_session_factory import TradingSessionFactory
from config.settings import load_settings
from infrastructure.tinvest.client_factory import TInvestClientFactory
from infrastructure.tinvest.sandbox_account_provider import (
    TInvestSandboxAccountProvider,
)
from strategy.grid_engine import GridEngineConfig, GridLevel


def main() -> None:
    settings = load_settings()

    factory = TradingSessionFactory(
        settings=settings,
    )

    # Временный уровень выше текущей цены.
    # Чтобы гарантированно получить сигнал BUY после просадки и отскока.
    context = factory.create_sandbox_session(
        ticker="SBER",
        sandbox_deposit=Decimal("100000"),
        levels=[
            GridLevel(
                index=1,
                price=Decimal("325"),
            )
        ],
        grid_config=GridEngineConfig(
            quantity=1,
            entry_rebound_percent=Decimal("0.01"),
            entry_limit_offset_percent=Decimal("0.01"),
        ),
    )

    print("Sandbox account:", context.sandbox_account_id)
    print("Ticker:", context.ticker)
    print("Current price:", context.current_price)
    print("Sandbox balance:", context.sandbox_balance)

    prices = [
        context.current_price,
        context.current_price * Decimal("0.995"),
        context.current_price * Decimal("0.990"),
        context.current_price * Decimal("0.992"),
        context.current_price * Decimal("0.995"),
    ]

    try:
        for price in prices:
            price = price.quantize(
                Decimal("0.01"),
            )

            placed_orders = context.session.on_price(
                price=price,
            )

            print("PRICE:", price)
            print("PLACED ORDERS:", placed_orders)

            if placed_orders:
                break

    finally:
        context.session.stop()

        token = (
            settings.tinvest_sandbox_token
            or settings.tinvest_token
        )

        sandbox_account_provider = TInvestSandboxAccountProvider(
            client_factory=TInvestClientFactory(
                token=token,
            ),
        )

        sandbox_account_provider.close_account(
            account_id=context.sandbox_account_id,
        )

        print("Sandbox account closed")


if __name__ == "__main__":
    main()
