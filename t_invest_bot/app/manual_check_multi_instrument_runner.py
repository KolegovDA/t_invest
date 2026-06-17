from decimal import Decimal

from application.multi_instrument_sandbox_bot_runner import (
    MultiInstrumentSandboxBotRunner,
)
from application.multi_instrument_session_config import (
    InstrumentConfig,
    MultiInstrumentSessionConfig,
)
from application.multi_instrument_trading_session_factory import (
    MultiInstrumentTradingSessionFactory,
)
from config.settings import load_settings


def main() -> None:
    settings = load_settings()

    factory = MultiInstrumentTradingSessionFactory(
        settings=settings,
    )

    config = MultiInstrumentSessionConfig(
        sandbox_deposit=Decimal("100000"),
        instruments=[
            InstrumentConfig(
                ticker="SBER",
                levels_count=20,
                quantity=1,
            ),
            InstrumentConfig(
                ticker="GAZP",
                levels_count=20,
                quantity=1,
            ),
            InstrumentConfig(
                ticker="LKOH",
                levels_count=20,
                quantity=1,
            ),
        ],
    )

    context = factory.create_sandbox_session(
        config=config,
    )

    runner = MultiInstrumentSandboxBotRunner(
        session=context.session,
        price_provider=context.price_provider,
        instrument_ids_by_ticker=context.instrument_ids_by_ticker,
        tickers_by_instrument_id=context.tickers_by_instrument_id,
        portfolio_manager=context.portfolio_manager,
        trade_capital_service=context.trade_capital_service,
        polling_interval_seconds=5,
    )

    print("Sandbox account:", context.sandbox_account_id)
    print("Instruments:", context.instrument_ids_by_ticker)

    try:
        runner.run(
            iterations=5,
        )

    finally:
        context.close()
        print("Sandbox closed")


if __name__ == "__main__":
    main()
