from __future__ import annotations

from dataclasses import dataclass

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
    api_usage_repository: object

    polling_interval_seconds: int = 10

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

        factory = (
            MultiInstrumentTradingSessionFactory(
                settings=self.settings,
            )
        )

        context = self._create_live_context(
            factory=factory,
            state=state,
            config=config,
        )

        restored_state = (
            self.state_service.restore(
                context=context,
                session_id=(
                    state.session_id
                ),
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

        runner = WebRunnerService(
            context=context,
            api_usage_repository=(
                self.api_usage_repository
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
            lifecycle_status=(
                "DRAINING"
                if state.status.upper() == "DRAINING"
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
                    int(quantity),
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
            instrument.entry_rebound_percent = (
                config.entry_rebound_percent
            )
            instrument.entry_limit_offset_percent = (
                config.entry_limit_offset_percent
            )
            instrument.exit_limit_offset_percent = (
                config.exit_limit_offset_percent
            )
            instrument.trailing_percent = (
                config.trailing_percent
            )
            instrument.min_profit_percent = (
                config.min_profit_percent
            )
            instrument.take_profit_buffer_percent = (
                config.take_profit_buffer_percent
            )
            instrument.min_open_positions_for_compensation = (
                config.min_open_positions_for_compensation
            )
            instrument.compensation_multiplier = (
                config.compensation_multiplier
            )

        return instrument
