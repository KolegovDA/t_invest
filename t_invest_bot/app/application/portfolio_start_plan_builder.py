from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from application.multi_instrument_session_config import (
    MultiInstrumentSessionConfig,
)
from application.multi_instrument_session_context import (
    MultiInstrumentSessionContext,
)
from application.portfolio_orchestrator import (
    PortfolioOrchestrator,
    PortfolioStartPlan,
)
from infrastructure.tinvest.history_provider import TInvestHistoryProvider
from strategy.history_analyzer import HistoryAnalyzer


@dataclass(slots=True)
class PortfolioStartPlanBuilder:
    history_provider: TInvestHistoryProvider
    orchestrator: PortfolioOrchestrator

    def build(
        self,
        config: MultiInstrumentSessionConfig,
        context: MultiInstrumentSessionContext,
    ) -> PortfolioStartPlan:
        prices_by_ticker: dict[str, Decimal] = {}
        price_ranges_by_ticker: dict[str, tuple[Decimal, Decimal]] = {}

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

            candles = self.history_provider.get_daily_candles(
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

        return self.orchestrator.build_start_plan(
            config=config,
            price_ranges_by_ticker=price_ranges_by_ticker,
            prices_by_ticker=prices_by_ticker,
            available_cash=context.sandbox_balance,
        )
