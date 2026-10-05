from __future__ import annotations

from dataclasses import dataclass
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from typing import Any

from application.multi_instrument_session_config import (
    InstrumentConfig,
    MultiInstrumentSessionConfig,
)
from application.trading_settings_service import TradingSettingsService
from application.sandbox_trading_session import (
    SandboxTradingSession,
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
from infrastructure.tinvest.candles_mapper import (
    TInvestCandlesMapper,
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
from strategy.grid_builder import GridBuilder
from strategy.grid_engine import GridEngine
from strategy.history_analyzer import (
    HistoryAnalyzer,
)


@dataclass(slots=True)
class SessionInstrumentManager:
    """
    Добавление и удаление
    инструментов в работающую
    мульти-инструментную
    сессию.

    Используется авторежимом
    v1.1 для ребаланса после
    полного закрытия сетки.
    """

    knowledge_engine: Any = None

    operation_log: Any = None

    commission_service: Any = None

    broker: str | None = None

    trading_settings_service: TradingSettingsService | None = None

    instrument_availability_check: Any = None

    history_years: int = 3

    exclude_first_days: int = 7

    def add_instrument(
        self,
        context: Any,

        ticker: str,

        levels_count: int,

        quantity: int,

        registry: Any = None,
    ) -> str | None:
        normalized = (
            ticker
            .strip()
            .upper()
        )

        existing = (
            context
            .instrument_ids_by_ticker
            .get(
                normalized
            )
        )

        if (
            existing
            is not None
        ):
            return (
                existing
            )

        if self.instrument_availability_check is not None:
            self.instrument_availability_check(normalized)

        (
            executor,

            order_state_provider,
        ) = (
            self
            ._resolve_executors(
                context=(
                    context
                ),
            )
        )

        if (
            executor
            is None
            or (
                order_state_provider
                is None
            )
        ):
            raise ValueError(
                "no order executor "
                "available to add "
                "instrument"
            )

        client_factory = (
            context
            .price_provider
            .client_factory
        )

        instrument = (
            TInvestInstrumentProvider(
                client_factory=(
                    client_factory
                ),

                mapper=(
                    TInvestInstrumentMapper()
                ),
            )
            .find_share_by_ticker(
                ticker=(
                    normalized
                ),
            )
        )

        if (
            instrument
            is None
        ):
            raise ValueError(
                "Instrument not "
                "found: "
                f"{normalized}"
            )

        date_to = (
            datetime
            .now(
                timezone
                .utc
            )
        )

        date_from = (
            date_to
            - timedelta(
                days=(
                    365
                    * (
                        self
                        .history_years
                    )
                ),
            )
        )

        history_provider = (
            TInvestHistoryProvider(
                client_factory=(
                    client_factory
                ),

                mapper=(
                    TInvestCandlesMapper()
                ),
            )
        )

        candles = (
            history_provider
            .get_daily_candles(
                instrument_id=(
                    instrument
                    .id
                ),

                date_from=(
                    date_from
                ),

                date_to=(
                    date_to
                ),
            )
        )

        price_range = (
            HistoryAnalyzer(
                exclude_first_days=(
                    self
                    .exclude_first_days
                ),
            )
            .calculate_range(
                candles=(
                    candles
                ),
            )
        )

        current_price = (
            context
            .price_provider
            .get_mid_price(
                instrument_uid=(
                    instrument
                    .id
                ),
            )
        )

        grid_builder = (
            GridBuilder(
                levels_count=(
                    levels_count
                ),
            )
        )

        levels = (
            grid_builder
            .build_from_range(
                min_price=(
                    price_range
                    .min_price
                ),

                current_price=(
                    current_price
                ),
            )
        )

        grid_step = (
            grid_builder
            .calculate_step(
                min_price=(
                    price_range
                    .min_price
                ),

                current_price=(
                    current_price
                ),
            )
        )

        instrument_config = (
            InstrumentConfig(
                ticker=(
                    normalized
                ),

                levels_count=(
                    levels_count
                ),

                quantity=(
                    quantity
                ),

                history_years=(
                    self
                    .history_years
                ),

                exclude_first_days=(
                    self
                    .exclude_first_days
                ),
            )
        )

        if self.trading_settings_service is not None and self.broker is not None:
            self.trading_settings_service.apply_to_config(
                MultiInstrumentSessionConfig(instruments=[instrument_config]),
                self.broker,
            )

        grid_engine = (
            GridEngine(
                instrument_id=(
                    instrument
                    .id
                ),

                levels=(
                    levels
                ),

                config=(
                    instrument_config
                    .to_grid_engine_config()
                ),

                session_start_price=(
                    current_price
                ),

                grid_step=(
                    grid_step
                ),
            )
        )

        live_order_manager = (
            LiveOrderManager(
                account_id=(
                    context
                    .account_id
                ),

                order_executor=(
                    executor
                ),

                trade_capital_service=(
                    context
                    .trade_capital_service
                ),
            )
        )

        order_state_tracker = (
            OrderStateTracker(
                account_id=(
                    context
                    .account_id
                ),

                live_order_manager=(
                    live_order_manager
                ),

                order_state_provider=(
                    order_state_provider
                ),
            )
        )

        session = (
            SandboxTradingSession(
                grid_engine=(
                    grid_engine
                ),

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
                            context
                            .portfolio_manager
                        ),

                        knowledge_engine=(
                            self
                            .knowledge_engine
                        ),

                        operation_log=(
                            self
                            .operation_log
                        ),

                        ticker=(
                            normalized
                        ),

                        trading_account_id=(
                            context
                            .account_id
                        ),

                        commission_service=(
                            self
                            .commission_service
                        ),

                        broker=(
                            self.broker
                        ),
                    )
                ),
            )
        )

        context\
            .session\
            .sessions[
                instrument
                .id
            ] = session

        context\
            .instrument_ids_by_ticker[
                normalized
            ] = (
                instrument
                .id
            )

        context\
            .tickers_by_instrument_id[
                instrument
                .id
            ] = (
                normalized
            )

        if (
            registry
            is not None
        ):
            registry\
                .register_multi_session(
                    session=(
                        context
                        .session
                    ),

                    instrument_ids_by_ticker={
                        normalized: (
                            instrument
                            .id
                        ),
                    },
                )

        return (
            instrument
            .id
        )

    def remove_instrument(
        self,
        context: Any,

        ticker: str,

        registry: Any = None,
    ) -> bool:
        normalized = (
            ticker
            .strip()
            .upper()
        )

        instrument_id = (
            context
            .instrument_ids_by_ticker
            .pop(
                normalized,

                None,
            )
        )

        if (
            instrument_id
            is None
        ):
            return False

        session = (
            context
            .session
            .sessions
            .pop(
                instrument_id,

                None,
            )
        )

        if (
            session
            is not None
        ):
            try:
                session.stop()

            except Exception:
                pass

        reservation_manager = (
            context
            .trade_capital_service
            .reservation_manager
        )

        for key in [
            key

            for key in list(
                reservation_manager
                .reservations
                .keys()
            )

            if (
                key[0]
                == (
                    instrument_id
                )
            )
        ]:
            reservation_manager\
                .release(
                    instrument_id=(
                        key[0]
                    ),

                    level_index=(
                        key[1]
                    ),
                )

        context\
            .tickers_by_instrument_id\
            .pop(
                instrument_id,

                None,
            )

        if (
            registry
            is not None
        ):
            registry\
                .unregister(
                    ticker=(
                        normalized
                    ),
                )

        return True

    def _resolve_executors(
        self,
        context: Any,
    ) -> (
        tuple[
            Any | None,

            Any | None,
        ]
    ):
        executor = getattr(
            context,

            "order_executor",

            None,
        )

        order_state_provider = getattr(
            context,

            "order_state_provider",

            None,
        )

        if (
            executor
            is not None
            and (
                order_state_provider
                is not None
            )
        ):
            return (
                executor,

                order_state_provider,
            )

        sessions = getattr(
            getattr(
                context,

                "session",
            ),

            "sessions",

            None,
        )

        if not sessions:
            return (
                executor,

                order_state_provider,
            )

        for session in (
            sessions
            .values()
        ):
            if (
                executor
                is None
            ):
                executor = getattr(
                    session
                    .live_order_manager,

                    "order_executor",

                    None,
                )

            if (
                order_state_provider
                is None
            ):
                tracker = getattr(
                    session,

                    "order_state_tracker",

                    None,
                )

                if (
                    tracker
                    is not None
                ):
                    order_state_provider = getattr(
                        tracker,

                        "order_state_provider",

                        None,
                    )

            break

        return (
            executor,

            order_state_provider,
        )
