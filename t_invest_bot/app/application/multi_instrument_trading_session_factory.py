from dataclasses import dataclass
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from typing import Any

from application.multi_instrument_sandbox_session import (
    MultiInstrumentSandboxSession,
)
from application.multi_instrument_session_config import (
    MultiInstrumentSessionConfig,
)
from application.multi_instrument_session_context import (
    MultiInstrumentSessionContext,
)
from application.portfolio_manager import (
    PortfolioManager,
)
from application.sandbox_trading_session import (
    SandboxTradingSession,
)
from application.trade_capital_service import (
    TradeCapitalService,
)
from application.trade_event_handler import (
    TradeEventHandler,
)
from broker.live_order_manager import (
    LiveOrderManager,
)
from broker.order_execution_event_mapper import (
    OrderExecutionEventMapper,
)
from broker.order_state_tracker import (
    OrderStateTracker,
)
from config.settings import Settings
from domain.portfolio import Portfolio
from infrastructure.tinvest.candles_mapper import (
    TInvestCandlesMapper,
)
from infrastructure.tinvest.client_factory import (
    TInvestClientFactory,
)
from infrastructure.tinvest.history_provider import (
    TInvestHistoryProvider,
)
from infrastructure.tinvest.instrument_mapper import (
    TInvestInstrumentMapper,
)
from infrastructure.tinvest.instrument_provider import (
    TInvestInstrumentProvider,
)
from infrastructure.tinvest.last_price_provider import (
    TInvestLastPriceProvider,
)
from infrastructure.tinvest.live_balance_provider import (
    TInvestLiveBalanceProvider,
)
from infrastructure.tinvest.live_order_executor import (
    TInvestLiveOrderExecutor,
)
from infrastructure.tinvest.live_order_state_provider import (
    TInvestLiveOrderStateProvider,
)
from infrastructure.tinvest.quotation_mapper import (
    TInvestQuotationMapper,
)
from infrastructure.tinvest.sandbox_account_provider import (
    TInvestSandboxAccountProvider,
)
from infrastructure.tinvest.sandbox_order_executor import (
    TInvestSandboxOrderExecutor,
)
from infrastructure.tinvest.sandbox_order_state_provider import (
    TInvestSandboxOrderStateProvider,
)
from portfolio.capital_reservation_manager import (
    CapitalReservationManager,
)
from strategy.grid_builder import GridBuilder
from strategy.grid_engine import GridEngine
from strategy.history_analyzer import (
    HistoryAnalyzer,
)


@dataclass(slots=True)
class MultiInstrumentTradingSessionFactory:
    settings: Settings

    def create_sandbox_session(
        self,
        config: MultiInstrumentSessionConfig,
    ) -> MultiInstrumentSessionContext:
        token = (
            self.settings.tinvest_sandbox_token
            or self.settings.tinvest_token
        )

        if not token:
            raise ValueError(
                "T-Invest sandbox token is not configured"
            )

        client_factory = TInvestClientFactory(
            token=token,
        )

        sandbox_account_provider = (
            TInvestSandboxAccountProvider(
                client_factory=client_factory,
            )
        )

        sandbox_account_id = (
            self.settings.selected_sandbox_account_id
        )

        created_sandbox_account = False

        if sandbox_account_id is None:
            sandbox_account_id = (
                sandbox_account_provider.open_account()
            )
            created_sandbox_account = True

        sandbox_balance = (
            sandbox_account_provider.pay_in(
                account_id=sandbox_account_id,
                amount=config.sandbox_deposit,
            )
        )

        try:
            return self._create_context(
                config=config,
                client_factory=client_factory,
                account_id=sandbox_account_id,
                available_cash=sandbox_balance,
                order_executor=(
                    TInvestSandboxOrderExecutor(
                        client_factory=client_factory,
                        quotation_mapper=(
                            TInvestQuotationMapper()
                        ),
                    )
                ),
                order_state_provider=(
                    TInvestSandboxOrderStateProvider(
                        client_factory=client_factory,
                    )
                ),
                sandbox_account_provider=(
                    sandbox_account_provider
                ),
                close_account_on_close=(
                    created_sandbox_account
                ),
                is_live=False,
            )

        except Exception:
            if created_sandbox_account:
                sandbox_account_provider.close_account(
                    account_id=sandbox_account_id,
                )

            raise

    def create_live_session(
        self,
        config: MultiInstrumentSessionConfig,
    ) -> MultiInstrumentSessionContext:
        token = self.settings.tinvest_token

        if not token:
            raise ValueError(
                "Production T-Invest token "
                "is not configured"
            )

        account_id = (
            self.settings.tinvest_live_account_id
        )

        if not account_id:
            raise ValueError(
                "TINVEST_LIVE_ACCOUNT_ID "
                "is not configured"
            )

        client_factory = TInvestClientFactory(
            token=token,
        )

        available_cash = (
            TInvestLiveBalanceProvider(
                client_factory=client_factory,
            ).get_rub_balance(
                account_id=account_id,
            )
        )

        if available_cash <= 0:
            raise ValueError(
                "Live account has no available "
                "RUB balance"
            )

        return self._create_context(
            config=config,
            client_factory=client_factory,
            account_id=account_id,
            available_cash=available_cash,
            order_executor=(
                TInvestLiveOrderExecutor(
                    client_factory=client_factory,
                    quotation_mapper=(
                        TInvestQuotationMapper()
                    ),
                )
            ),
            order_state_provider=(
                TInvestLiveOrderStateProvider(
                    client_factory=client_factory,
                )
            ),
            sandbox_account_provider=None,
            close_account_on_close=False,
            is_live=True,
        )

    def _create_context(
        self,
        config: MultiInstrumentSessionConfig,
        client_factory: TInvestClientFactory,
        account_id: str,
        available_cash,
        order_executor: Any,
        order_state_provider: Any,
        sandbox_account_provider: (
            TInvestSandboxAccountProvider | None
        ),
        close_account_on_close: bool,
        is_live: bool,
    ) -> MultiInstrumentSessionContext:
        instrument_provider = (
            TInvestInstrumentProvider(
                client_factory=client_factory,
                mapper=TInvestInstrumentMapper(),
            )
        )

        price_provider = (
            TInvestLastPriceProvider(
                client_factory=client_factory,
            )
        )

        history_provider = (
            TInvestHistoryProvider(
                client_factory=client_factory,
                mapper=TInvestCandlesMapper(),
            )
        )

        portfolio_manager = PortfolioManager(
            portfolio=Portfolio(
                cash=available_cash,
            )
        )

        trade_capital_service = (
            TradeCapitalService(
                portfolio_manager=(
                    portfolio_manager
                ),
                reservation_manager=(
                    CapitalReservationManager(
                        available_cash=(
                            available_cash
                        ),
                    )
                ),
            )
        )

        sessions: dict[
            str,
            SandboxTradingSession,
        ] = {}

        instrument_ids_by_ticker: dict[
            str,
            str,
        ] = {}

        tickers_by_instrument_id: dict[
            str,
            str,
        ] = {}

        for instrument_config in (
            config.instruments
        ):
            instrument = (
                instrument_provider
                .find_share_by_ticker(
                    ticker=(
                        instrument_config.ticker
                    ),
                )
            )

            if instrument is None:
                raise ValueError(
                    "Instrument not found: "
                    f"{instrument_config.ticker}"
                )

            instrument_ids_by_ticker[
                instrument.ticker
            ] = instrument.id

            tickers_by_instrument_id[
                instrument.id
            ] = instrument.ticker

            date_to = datetime.now(
                timezone.utc
            )

            date_from = (
                date_to
                - timedelta(
                    days=(
                        365
                        * instrument_config
                        .history_years
                    ),
                )
            )

            candles = (
                history_provider
                .get_daily_candles(
                    instrument_id=(
                        instrument.id
                    ),
                    date_from=date_from,
                    date_to=date_to,
                )
            )

            price_range = HistoryAnalyzer(
                exclude_first_days=(
                    instrument_config
                    .exclude_first_days
                ),
            ).calculate_range(
                candles=candles,
            )

            current_price = (
                price_provider
                .get_last_price(
                    instrument_uid=(
                        instrument.id
                    ),
                )
            )

            levels = GridBuilder(
                levels_count=(
                    instrument_config
                    .levels_count
                ),
            ).build_from_range(
                min_price=(
                    price_range.min_price
                ),
                current_price=current_price,
            )

            grid_engine = GridEngine(
                instrument_id=instrument.id,
                levels=levels,
                config=(
                    instrument_config
                    .to_grid_engine_config()
                ),
            )

            live_order_manager = (
                LiveOrderManager(
                    account_id=account_id,
                    order_executor=(
                        order_executor
                    ),
                    trade_capital_service=(
                        trade_capital_service
                    ),
                )
            )

            order_state_tracker = (
                OrderStateTracker(
                    account_id=account_id,
                    live_order_manager=(
                        live_order_manager
                    ),
                    order_state_provider=(
                        order_state_provider
                    ),
                )
            )

            sessions[
                instrument.id
            ] = SandboxTradingSession(
                grid_engine=grid_engine,
                live_order_manager=(
                    live_order_manager
                ),
                order_state_tracker=(
                    order_state_tracker
                ),
                execution_event_mapper=(
                    OrderExecutionEventMapper()
                ),
                trade_event_handler=(
                    TradeEventHandler(
                        portfolio_manager=(
                            portfolio_manager
                        ),
                    )
                ),
            )

        return MultiInstrumentSessionContext(
            session=(
                MultiInstrumentSandboxSession(
                    sessions=sessions,
                )
            ),
            portfolio_manager=(
                portfolio_manager
            ),
            trade_capital_service=(
                trade_capital_service
            ),
            price_provider=price_provider,

            # Для обратной совместимости
            sandbox_account_provider=(
                sandbox_account_provider
            ),
            sandbox_account_id=account_id,
            sandbox_balance=available_cash,

            instrument_ids_by_ticker=(
                instrument_ids_by_ticker
            ),
            tickers_by_instrument_id=(
                tickers_by_instrument_id
            ),

            is_live=is_live,
            close_account_on_close=(
                close_account_on_close
            ),
        )
