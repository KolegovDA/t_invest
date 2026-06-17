from datetime import datetime, timedelta, timezone
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
from application.start_plan_reporter import StartPlanReporter
from config.settings import load_settings
from infrastructure.tinvest.candles_mapper import TInvestCandlesMapper
from infrastructure.tinvest.client_factory import TInvestClientFactory
from infrastructure.tinvest.history_provider import TInvestHistoryProvider
from strategy.history_analyzer import HistoryAnalyzer


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
    price_ranges_by_ticker: dict[str, tuple[Decimal, Decimal]] = {}

    token = settings.tinvest_sandbox_token or settings.tinvest_token

    history_provider = TInvestHistoryProvider(
        client_factory=TInvestClientFactory(
            token=token,
        ),
        mapper=TInvestCandlesMapper(),
    )

    date_to = datetime.now(timezone.utc)

    for instrument_config in config.instruments:
        instrument_id = context.instrument_ids_by_ticker[
            instrument_config.ticker
        ]

        prices_by_ticker[
            instrument_config.ticker
        ] = context.price_provider.get_last_price(
            instrument_uid=instrument_id,
        )

        date_from = date_to - timedelta(
            days=365 * instrument_config.history_years,
        )

        candles = history_provider.get_daily_candles(
            instrument_id=instrument_id,
            date_from=date_from,
            date_to=date_to,
        )

        price_range = HistoryAnalyzer(
            exclude_first_days=instrument_config.exclude_first_days,
        ).calculate_range(
            candles=candles,
        )

        price_ranges_by_ticker[
            instrument_config.ticker
        ] = (
            price_range.min_price,
            price_range.max_price,
        )

    plan = PortfolioOrchestrator().build_start_plan(
        config=config,
        price_ranges_by_ticker=price_ranges_by_ticker,
        prices_by_ticker=prices_by_ticker,
        available_cash=context.sandbox_balance,
    )

    StartPlanReporter().print(
        plan,
    )

    print()
    print("Sandbox account:", context.sandbox_account_id)
    print("Sessions:", len(context.session.sessions))

    try:
        print()
        print("INSTRUMENTS:")

        for ticker, instrument_id in context.instrument_ids_by_ticker.items():
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
