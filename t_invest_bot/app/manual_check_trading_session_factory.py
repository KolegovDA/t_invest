from decimal import Decimal

from application.grid_session_config import GridSessionConfig
from application.trading_session_factory import TradingSessionFactory
from config.settings import load_settings


def main() -> None:
    settings = load_settings()

    factory = TradingSessionFactory(
        settings=settings,
    )

    config = GridSessionConfig(
        ticker="SBER",
        levels_count=5,
        quantity=1,
        sandbox_deposit=Decimal("100000"),
        entry_rebound_percent=Decimal("0.01"),
        entry_limit_offset_percent=Decimal("0.01"),
    )

    context = factory.create_sandbox_session(
        config=config,
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
        context.close()
        print("Sandbox account closed")


if __name__ == "__main__":
    main()
