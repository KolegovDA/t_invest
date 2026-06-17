from decimal import Decimal

from application.multi_instrument_session_config import (
    InstrumentConfig,
    MultiInstrumentSessionConfig,
)
from application.multi_instrument_trading_session_factory import (
    MultiInstrumentTradingSessionFactory,
)
from application.portfolio_orchestrator import PortfolioOrchestrator
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

    prices_by_ticker: dict[str, Decimal] = {}

    for ticker, instrument_id in context.instrument_ids_by_ticker.items():
        prices_by_ticker[ticker] = context.price_provider.get_last_price(
            instrument_uid=instrument_id,
        )

    plan = PortfolioOrchestrator().build_start_plan(
        config=config,
        prices_by_ticker=prices_by_ticker,
        available_cash=context.sandbox_balance,
    )

    print("START PLAN:")
    print("Available cash:", plan.available_cash)
    print("Total required deposit:", plan.total_required_deposit)
    print("Can start:", plan.can_start)

    for instrument_plan in plan.instruments:
        print(instrument_plan)

    print()

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
