from decimal import Decimal

from application.multi_instrument_session_config import (
    InstrumentConfig,
    MultiInstrumentSessionConfig,
)
from application.multi_instrument_trading_session_factory import (
    MultiInstrumentTradingSessionFactory,
)
from application.session_reporter import SessionReporter
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

    reporter = SessionReporter(
        portfolio_manager=context.portfolio_manager,
        trade_capital_service=context.trade_capital_service,
    )

    print("Sandbox account:", context.sandbox_account_id)
    print("Sessions:", len(context.session.sessions))

    try:
        print()
        print("INSTRUMENTS:")

        for ticker, instrument_id in (
            context.instrument_ids_by_ticker.items()
        ):
            print(
                f"{ticker}: {instrument_id}"
            )

        print()

        reporter.print_all()

    finally:
        context.close()
        print("Sandbox closed")


if __name__ == "__main__":
    main()
