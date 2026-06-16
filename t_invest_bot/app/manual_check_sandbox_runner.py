from decimal import Decimal

from application.grid_session_config import GridSessionConfig
from application.sandbox_bot_runner import SandboxBotRunner
from application.trading_session_factory import TradingSessionFactory
from config.settings import load_settings


def main() -> None:
    settings = load_settings()

    factory = TradingSessionFactory(
        settings=settings,
    )

    config = GridSessionConfig(
        ticker="SBER",
        levels_count=20,
        quantity=1,
        sandbox_deposit=Decimal("100000"),
    )

    context = factory.create_sandbox_session(
        config=config,
    )

    print("Sandbox account:", context.sandbox_account_id)
    print("Ticker:", context.ticker)
    print("Current price:", context.current_price)
    print("Sandbox balance:", context.sandbox_balance)
    print("Price range:", context.price_range)

    print("Levels:")
    for level in context.levels:
        print(level)

    runner = SandboxBotRunner(
        session=context.session,
        instrument_id=context.instrument_id,
        price_provider=context.price_provider,
        portfolio_manager=context.portfolio_manager,
        trade_capital_service=context.trade_capital_service,
        polling_interval_seconds=5,
    )

    try:
        runner.run(
            iterations=10,
        )

    finally:
        context.close()
        print("Sandbox closed")


if __name__ == "__main__":
    main()
