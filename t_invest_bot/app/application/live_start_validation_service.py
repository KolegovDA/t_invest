from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from application.multi_instrument_session_config import (
    MultiInstrumentSessionConfig,
)
from application.multi_instrument_trading_session_factory import (
    MultiInstrumentTradingSessionFactory,
)
from application.portfolio_orchestrator import (
    PortfolioOrchestrator,
)
from application.trading_account_service import (
    TradingAccountService,
)

from domain.trading_account import (
    BrokerType,
    TradingAccountMode,
)

from infrastructure.brokers.registry import (
    BrokerRegistry,
)


@dataclass(slots=True)
class LiveStartValidationInstrument:
    ticker: str

    instrument_uid: str

    current_price: Decimal

    min_grid_price: Decimal

    grid_step: Decimal

    levels_count: int

    quantity: int


@dataclass(slots=True)
class LiveStartValidationResult:
    success: bool

    trading_account_id: str

    broker: str

    broker_account_id: str

    account_name: str

    available_cash: Decimal

    total_required_deposit: Decimal

    remaining_cash: Decimal

    missing_cash: Decimal

    can_start: bool

    can_start_forced: bool

    capital_utilization_percent: Decimal

    buy_commission_percent: Decimal

    sell_commission_percent: Decimal

    instruments: list[
        LiveStartValidationInstrument
    ]


@dataclass(slots=True)
class LiveStartValidationService:
    trading_account_service: (
        TradingAccountService
    )

    broker_registry: (
        BrokerRegistry
    )

    session_factory: (
        MultiInstrumentTradingSessionFactory
    )

    portfolio_orchestrator: (
        PortfolioOrchestrator
    )

    def validate(
        self,

        trading_account_id: str,

        config: MultiInstrumentSessionConfig,
    ) -> LiveStartValidationResult:
        #
        # 1.
        # Загружаем локальный
        # ESM account.
        #
        try:
            account = (
                self
                .trading_account_service
                .get(
                    trading_account_id
                )
            )

        except KeyError as error:
            raise ValueError(
                "Trading account "
                "not found"
            ) from error

        if not account.enabled:
            raise ValueError(
                "Trading account "
                "is disabled"
            )

        if (
            account.mode
            != TradingAccountMode.LIVE
        ):
            raise ValueError(
                "Trading account "
                "is not LIVE"
            )

        #
        # Сейчас реальный торговый
        # SessionFactory реализован
        # только для T-Invest.
        #
        if (
            account.broker
            != BrokerType.TINVEST
        ):
            raise ValueError(
                "Live trading for broker "
                f"{account.broker.value} "
                "is not supported yet"
            )

        #
        # 2.
        # Получаем credentials.
        #
        credentials = (
            self
            .trading_account_service
            .get_credentials(
                account.id
            )
        )

        token = (
            credentials.require(
                "token"
            )
        )

        #
        # 3.
        # Проверяем адаптер брокера.
        #
        try:
            adapter = (
                self
                .broker_registry
                .get(
                    account.broker
                )
            )

        except KeyError as error:
            raise ValueError(
                "Broker adapter "
                "is not registered"
            ) from error

        connection = (
            adapter.test_connection(
                credentials=(
                    credentials
                ),

                broker_account_id=(
                    account
                    .broker_account_id
                ),

                mode=(
                    account.mode
                ),
            )
        )

        if not connection.success:
            raise ValueError(
                "Broker connection "
                "failed: "
                f"{connection.error}"
            )

        if not connection.account_found:
            raise ValueError(
                "Broker account "
                "was not found"
            )

        #
        # 4.
        # Комиссии выбранного
        # аккаунта.
        #
        buy_commission_percent = (
            account
            .get_expected_buy_commission_percent()
        )

        sell_commission_percent = (
            account
            .get_expected_sell_commission_percent()
        )

        #
        # 5.
        # Создаём торговый context.
        #
        # ВАЖНО:
        #
        # runner здесь НЕ создаётся.
        #
        # on_price() не вызывается.
        #
        # place_limit_buy/sell()
        # не вызываются.
        #
        # Поэтому никаких новых
        # заявок данный метод
        # не выставляет.
        #
        context = (
            self
            .session_factory
            .create_live_session_for_account(
                config=config,

                token=token,

                broker_account_id=(
                    account
                    .broker_account_id
                ),

                buy_commission_percent=(
                    buy_commission_percent
                ),

                sell_commission_percent=(
                    sell_commission_percent
                ),
            )
        )

        #
        # 6.
        # Собираем реальные данные
        # построенных сеток.
        #
        prices_by_ticker: dict[
            str,
            Decimal,
        ] = {}

        price_ranges_by_ticker: dict[
            str,
            tuple[
                Decimal,
                Decimal,
            ],
        ] = {}

        validation_instruments: list[
            LiveStartValidationInstrument
        ] = []

        for instrument_config in (
            config.instruments
        ):
            ticker = (
                instrument_config
                .ticker
                .upper()
            )

            instrument_uid = (
                context
                .instrument_ids_by_ticker
                .get(
                    ticker
                )
            )

            if instrument_uid is None:
                raise ValueError(
                    "Instrument UID "
                    "was not resolved: "
                    f"{ticker}"
                )

            trading_session = (
                context
                .session
                .sessions
                .get(
                    instrument_uid
                )
            )

            if trading_session is None:
                raise ValueError(
                    "Trading session "
                    "was not created: "
                    f"{ticker}"
                )

            grid_engine = (
                trading_session
                .grid_engine
            )

            if not grid_engine.levels:
                raise ValueError(
                    "Grid has no levels: "
                    f"{ticker}"
                )

            current_price = (
                grid_engine
                .session_start_price
            )

            if current_price is None:
                raise ValueError(
                    "Session start price "
                    "is missing: "
                    f"{ticker}"
                )

            min_grid_price = min(
                level.price
                for level
                in grid_engine.levels
            )

            grid_step = (
                grid_engine
                .grid_step
            )

            if grid_step is None:
                raise ValueError(
                    "Grid step "
                    "is missing: "
                    f"{ticker}"
                )

            prices_by_ticker[
                ticker
            ] = (
                current_price
            )

            price_ranges_by_ticker[
                ticker
            ] = (
                min_grid_price,
                current_price,
            )

            validation_instruments.append(
                LiveStartValidationInstrument(
                    ticker=ticker,

                    instrument_uid=(
                        instrument_uid
                    ),

                    current_price=(
                        current_price
                    ),

                    min_grid_price=(
                        min_grid_price
                    ),

                    grid_step=(
                        grid_step
                    ),

                    levels_count=len(
                        grid_engine
                        .levels
                    ),

                    quantity=(
                        instrument_config
                        .quantity
                    ),
                )
            )

        #
        # 7.
        # Используем тот же
        # PortfolioOrchestrator,
        # что и при обычном
        # расчёте запуска.
        #
        available_cash = (
            context
            .portfolio_manager
            .portfolio
            .cash
        )

        plan = (
            self
            .portfolio_orchestrator
            .build_start_plan(
                config=config,

                price_ranges_by_ticker=(
                    price_ranges_by_ticker
                ),

                prices_by_ticker=(
                    prices_by_ticker
                ),

                available_cash=(
                    available_cash
                ),
            )
        )

        return (
            LiveStartValidationResult(
                success=True,

                trading_account_id=(
                    account.id
                ),

                broker=(
                    account
                    .broker
                    .value
                ),

                broker_account_id=(
                    account
                    .broker_account_id
                ),

                account_name=(
                    account.name
                ),

                available_cash=(
                    plan
                    .available_cash
                ),

                total_required_deposit=(
                    plan
                    .total_required_deposit
                ),

                remaining_cash=(
                    plan
                    .remaining_cash
                ),

                missing_cash=(
                    plan
                    .missing_cash
                ),

                can_start=(
                    plan
                    .can_start
                ),

                can_start_forced=(
                    plan
                    .can_start_forced
                ),

                capital_utilization_percent=(
                    plan
                    .capital_utilization_percent
                ),

                buy_commission_percent=(
                    buy_commission_percent
                ),

                sell_commission_percent=(
                    sell_commission_percent
                ),

                instruments=(
                    validation_instruments
                ),
            )
        )
