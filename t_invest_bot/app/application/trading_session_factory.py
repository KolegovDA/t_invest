from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from application.grid_session_config import GridSessionConfig
from application.portfolio_manager import PortfolioManager
from application.sandbox_trading_session import SandboxTradingSession
from application.trade_capital_service import TradeCapitalService
from application.trade_event_handler import TradeEventHandler
from broker.live_order_manager import LiveOrderManager
from broker.order_execution_event_mapper import OrderExecutionEventMapper
from broker.order_state_tracker import OrderStateTracker
from config.settings import Settings
from domain.portfolio import Portfolio
from infrastructure.tinvest.candles_mapper import TInvestCandlesMapper
from infrastructure.tinvest.client_factory import TInvestClientFactory
from infrastructure.tinvest.history_provider import TInvestHistoryProvider
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
from infrastructure.tinvest.sandbox_order_state_provider import (
    TInvestSandboxOrderStateProvider,
)
from portfolio.capital_reservation_manager import CapitalReservationManager
from strategy.grid_builder import GridBuilder
from strategy.grid_engine import GridEngine, GridLevel
from strategy.history_analyzer import HistoryAnalyzer, PriceRange


@dataclass(slots=True)
class SandboxTradingSessionContext:
    session: SandboxTradingSession
    portfolio_manager: PortfolioManager
    trade_capital_service: TradeCapitalService
    price_provider: TInvestLastPriceProvider
    sandbox_account_provider: TInvestSandboxAccountProvider
    sandbox_account_id: str
    instrument_id: str
    ticker: str
    current_price: Decimal
    sandbox_balance: Decimal
    price_range: PriceRange
    levels: list[GridLevel]

    def close(self) -> None:
        self.session.stop()

        self.sandbox_account_provider.close_account(
            account_id=self.sandbox_account_id,
        )


@dataclass(slots=True)
class TradingSessionFactory:
    settings: Settings

    def create_sandbox_session(
        self,
        config: GridSessionConfig,
    ) -> SandboxTradingSessionContext:
        token = (
            self.settings.tinvest_sandbox_token
            or self.settings.tinvest_token
        )

        if not token:
            raise ValueError("T-Invest sandbox token is not configured")

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

        history_provider = TInvestHistoryProvider(
            client_factory=client_factory,
            mapper=TInvestCandlesMapper(),
        )

        sandbox_account_provider = TInvestSandboxAccountProvider(
            client_factory=client_factory,
        )

        order_executor = TInvestSandboxOrderExecutor(
            client_factory=client_factory,
            quotation_mapper=TInvestQuotationMapper(),
        )

        instrument = instrument_provider.find_share_by_ticker(
            ticker=config.ticker,
        )

        if instrument is None:
            raise ValueError(f"Instrument not found: {config.ticker}")

        current_price = price_provider.get_last_price(
            instrument_uid=instrument.id,
        )

        date_to = datetime.now(timezone.utc)
        date_from = date_to - timedelta(
            days=365 * config.history_years,
        )

        candles = history_provider.get_daily_candles(
            instrument_id=instrument.id,
            date_from=date_from,
            date_to=date_to,
        )

        price_range = HistoryAnalyzer(
            exclude_first_days=config.exclude_first_days,
        ).calculate_range(
            candles=candles,
        )

        levels = GridBuilder(
            levels_count=config.levels_count,
        ).build_from_range(
            min_price=price_range.min_price,
            current_price=current_price,
        )

        sandbox_account_id = sandbox_account_provider.open_account()

        sandbox_balance = sandbox_account_provider.pay_in(
            account_id=sandbox_account_id,
            amount=config.sandbox_deposit,
        )

        portfolio_manager = PortfolioManager(
            portfolio=Portfolio(
                cash=sandbox_balance,
            )
        )

        trade_capital_service = TradeCapitalService(
            portfolio_manager=portfolio_manager,
            reservation_manager=CapitalReservationManager(
                available_cash=sandbox_balance,
            ),
        )

        grid_engine = GridEngine(
            instrument_id=instrument.id,
            levels=levels,
            config=config.to_grid_engine_config(),
        )

        live_order_manager = LiveOrderManager(
            account_id=sandbox_account_id,
            order_executor=order_executor,
            trade_capital_service=trade_capital_service,
        )

        order_state_provider = TInvestSandboxOrderStateProvider(
            client_factory=client_factory,
        )

        order_state_tracker = OrderStateTracker(
            account_id=sandbox_account_id,
            live_order_manager=live_order_manager,
            order_state_provider=order_state_provider,
        )

        session = SandboxTradingSession(
            grid_engine=grid_engine,
            live_order_manager=live_order_manager,
            order_state_tracker=order_state_tracker,
            execution_event_mapper=OrderExecutionEventMapper(),
            trade_event_handler=TradeEventHandler(
                portfolio_manager=portfolio_manager,
            ),
        )

        return SandboxTradingSessionContext(
            session=session,
            portfolio_manager=portfolio_manager,
            trade_capital_service=trade_capital_service,
            price_provider=price_provider,
            sandbox_account_provider=sandbox_account_provider,
            sandbox_account_id=sandbox_account_id,
            instrument_id=instrument.id,
            ticker=instrument.ticker,
            current_price=current_price,
            sandbox_balance=sandbox_balance,
            price_range=price_range,
            levels=levels,
        )
