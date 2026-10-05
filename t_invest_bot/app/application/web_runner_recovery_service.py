from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from application.bybit_session_factory import BybitSessionFactory
from application.multi_instrument_session_config import (
    InstrumentConfig,
    MultiInstrumentSessionConfig,
)
from application.multi_instrument_trading_session_factory import (
    MultiInstrumentTradingSessionFactory,
)
from application.trading_account_service import (
    TradingAccountService,
)
from application.trading_session_state_service import (
    TradingSessionStateService,
)
from application.trading_settings_service import TradingSettingsService
from application.web_runner_registry import (
    WebRunnerRegistry,
)
from application.web_runner_service import (
    WebRunnerService,
)
from config.settings import Settings
from domain.trading_account import (
    BrokerType,
    TradingAccountMode,
)
from domain.trading_state import (
    InstrumentTradingState,
    TradingSessionState,
)
from infrastructure.sqlite.api_usage_repository import SQLiteApiUsageRepository
from infrastructure.sqlite.trading_state_repository import (
    TradingStateRepository,
)


@dataclass(slots=True)
class WebRunnerRecoveryResult:
    restored: int = 0
    skipped: int = 0
    failed: int = 0


@dataclass(slots=True)
class WebRunnerRecoveryService:
    settings: Settings
    state_repository: TradingStateRepository
    state_service: TradingSessionStateService
    trading_account_service: TradingAccountService
    runner_registry: WebRunnerRegistry
    api_usage_repository: SQLiteApiUsageRepository

    reconciliation_journal: (
        object | None
    ) = None

    polling_interval_seconds: int = 10
    trading_settings_service: TradingSettingsService | None = None
    commission_service: Any = None
    operation_log: Any = None
    knowledge_engine: Any = None
    notifier: Any = None

    def recover_active_runners(
        self,
    ) -> WebRunnerRecoveryResult:
        result = WebRunnerRecoveryResult()

        # get_active() возвращает самые свежие snapshots первыми.
        # Если старые версии приложения оставили несколько RUNNING
        # snapshots одной и той же конфигурации, восстанавливаем
        # только самый свежий, а остальные автоматически закрываем.
        seen_recovery_keys: set[tuple] = set()

        for state in (
            self.state_repository
            .get_active()
        ):
            if (
                state.mode.lower()
                != "live"
            ):
                result.skipped += 1
                continue

            recovery_key = (
                self._build_recovery_key(
                    state
                )
            )

            if recovery_key in seen_recovery_keys:
                self._mark_duplicate_stopped(
                    state
                )

                result.skipped += 1

                print(
                    "RUNNER RECOVERY DUPLICATE STOPPED:",
                    state.session_id,
                    state.trading_account_id,
                )

                continue

            seen_recovery_keys.add(
                recovery_key
            )

            if (
                self.runner_registry
                .has_session_id(
                    state.session_id
                )
            ):
                result.skipped += 1
                continue

            try:
                self._recover_state(
                    state
                )
                result.restored += 1

            except Exception as error:
                result.failed += 1

                print(
                    "RUNNER RECOVERY FAILED:",
                    state.session_id,
                    repr(error),
                )

                try:
                    self.api_usage_repository.record(
                        source="runner",
                        operation="runner_recovery_failed",
                        weight=1,
                    )
                except Exception:
                    pass

        print(
            "RUNNER RECOVERY SUMMARY:",
            f"restored={result.restored}",
            f"skipped={result.skipped}",
            f"failed={result.failed}",
        )

        return result

    def _recover_state(
        self,
        state: TradingSessionState,
    ) -> None:
        config = self._build_config(
            state
        )
        if self.runner_registry is not None:
            self.runner_registry.ensure_instruments_available(
                state.trading_account_id,
                [instrument.ticker for instrument in config.instruments],
            )
        try:
            broker = self.trading_account_service.get(state.trading_account_id).broker.value if self.trading_account_service is not None else "tinvest"
        except KeyError:
            broker = "tinvest"
        if self.trading_settings_service is not None:
            config = self.trading_settings_service.apply_to_config(config, broker)

        factory = (
            MultiInstrumentTradingSessionFactory(
                settings=self.settings,
                commission_service=self.commission_service,
                operation_log=self.operation_log,
                knowledge_engine=self.knowledge_engine,
                notifier=self.notifier,
                broker=broker,
            )
        )

        context = self._create_live_context(
            factory=factory,
            state=state,
            config=config,
        )

        for trading_session in getattr(context.session, "sessions", {}).values():
            handler = trading_session.trade_event_handler
            handler.trading_account_id = state.trading_account_id
            handler.broker = broker

        restored_state = (
            self.state_service.restore(
                context=context,
                session_id=(
                    state.session_id
                ),
                use_current_rules=True,
            )
        )

        if restored_state is None:
            raise RuntimeError(
                "Trading state disappeared "
                "during recovery"
            )

        # Reconcile broker order states before the first new price tick.
        # Restored active broker orders are already present in the
        # LiveOrderManager at this point.
        context.session.poll_executions()
        self.state_service.save(
            context=context,
            session_id=state.session_id,
            trading_account_id=state.trading_account_id,
            status=state.status,
        )

        runner = WebRunnerService(
            context=context,
            api_usage_repository=(
                self.api_usage_repository
            ),
            reconciliation_journal=(
                self.reconciliation_journal
            ),
            polling_interval_seconds=(
                self.polling_interval_seconds
            ),
            state_service=(
                self.state_service
            ),
            session_id=(
                state.session_id
            ),
            trading_account_id=(
                state.trading_account_id
            ),
            planned_initial_capital=(
                state.initial_deposit
            ),
            commission_service=self.commission_service,
            operation_log=self.operation_log,
            lifecycle_status=(
                state.status.upper()
                if state.status.upper() in {"DRAINING", "STOPPING"}
                else "RUNNING"
            ),
        )

        self.runner_registry.start(
            runner=runner,
        )

        if (
            state.status.upper() == "DRAINING"
        ):
            runner.request_drain()

        try:
            self.api_usage_repository.record(
                source="runner",
                operation="runner_recovered",
                weight=1,
            )
        except Exception:
            pass

        print(
            "RUNNER RECOVERED:",
            state.session_id,
            state.trading_account_id,
        )

    def _create_live_context(
        self,
        factory: MultiInstrumentTradingSessionFactory,
        state: TradingSessionState,
        config: MultiInstrumentSessionConfig,
    ):
        try:
            account = (
                self.trading_account_service
                .get(
                    state.trading_account_id
                )
            )

        except KeyError:
            account = None

        if account is not None:
            if not account.enabled:
                raise RuntimeError(
                    "Trading account is disabled"
                )

            if account.broker == BrokerType.BYBIT:
                if account.mode != TradingAccountMode.LIVE or account.broker_account_id != state.broker_account_id:
                    raise RuntimeError("Saved Bybit account mode or ID mismatch")
                return BybitSessionFactory(
                    operation_log=self.operation_log, notifier=self.notifier,
                    commission_service=self.commission_service, knowledge_engine=self.knowledge_engine,
                ).create(config, self.trading_account_service.get_credentials(account.id), account.broker_account_id, account.id, (account.base_currency or "USDT").upper(), validate_entry=False)

            if (
                account.broker
                != BrokerType.TINVEST
            ):
                raise RuntimeError(
                    "Only T-Invest runner recovery "
                    "is supported currently"
                )

            if (
                account.mode
                != TradingAccountMode.LIVE
            ):
                raise RuntimeError(
                    "Saved LIVE runner references "
                    "a non-LIVE account"
                )

            if (
                account.broker_account_id
                != state.broker_account_id
            ):
                raise RuntimeError(
                    "Broker account mismatch for "
                    "saved ESM account"
                )

            credentials = (
                self.trading_account_service
                .get_credentials(
                    account.id
                )
            )

            return (
                factory
                .create_live_session_for_account(
                    config=config,
                    token=(
                        credentials.require(
                            "token"
                        )
                    ),
                    broker_account_id=(
                        account
                        .broker_account_id
                    ),
                    buy_commission_percent=(
                        account
                        .get_expected_buy_commission_percent()
                    ),
                    sell_commission_percent=(
                        account
                        .get_expected_sell_commission_percent()
                    ),
                )
            )

        # Compatibility with snapshots created before Account Manager.
        legacy_account_id = (
            self.settings
            .tinvest_live_account_id
        )

        if (
            legacy_account_id
            != state.broker_account_id
        ):
            raise RuntimeError(
                "Saved trading_account_id is not present "
                "in Account Manager and does not match "
                "the configured legacy LIVE account"
            )

        return factory.create_live_session(
            config=config,
        )

    def _mark_duplicate_stopped(
        self,
        state: TradingSessionState,
    ) -> None:
        state.status = "STOPPED"

        self.state_repository.save(
            state
        )

    @staticmethod
    def _build_recovery_key(
        state: TradingSessionState,
    ) -> tuple:
        instrument_keys = []

        for instrument in state.instruments:
            config = instrument.grid_config

            quantity = (
                config.quantity
                if config is not None
                else (
                    instrument.open_positions[0].quantity
                    if instrument.open_positions
                    else 1
                )
            )

            instrument_keys.append(
                (
                    instrument.ticker.upper(),
                    len(instrument.levels),
                    quantity,
                    getattr(config, "base_order_amount", None),
                )
            )

        instrument_keys.sort()

        return (
            state.trading_account_id,
            state.broker_account_id,
            state.mode.lower(),
            tuple(instrument_keys),
        )

    def _build_config(
        self,
        state: TradingSessionState,
    ) -> MultiInstrumentSessionConfig:
        instruments = [
            self._build_instrument_config(
                item
            )
            for item
            in state.instruments
        ]

        if not instruments:
            raise RuntimeError(
                "Saved runner has no instruments"
            )

        return MultiInstrumentSessionConfig(
            instruments=instruments,
        )

    @staticmethod
    def _build_instrument_config(
        state: InstrumentTradingState,
    ) -> InstrumentConfig:
        config = state.grid_config

        levels_count = len(
            state.levels
        )

        if levels_count <= 0:
            raise RuntimeError(
                "Saved instrument has no grid levels: "
                f"{state.ticker}"
            )

        quantity = (
            config.quantity
            if config is not None
            else (
                state.open_positions[0].quantity
                if state.open_positions
                else 1
            )
        )

        instrument = InstrumentConfig(
            ticker=state.ticker,
            levels_count=levels_count,
            quantity=quantity,
        )
        if config is not None:
            for field in ("base_order_amount", "order_amount_multiplier", "max_order_amount_multiplier", "quantity_step", "min_quantity", "min_order_amount"):
                setattr(instrument, field, getattr(config, field, getattr(instrument, field)))

        return instrument
