from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from application.multi_instrument_session_config import (
    InstrumentConfig,
    MultiInstrumentSessionConfig,
)
from application.multi_instrument_trading_session_factory import (
    MultiInstrumentTradingSessionFactory,
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
from domain.trading_state import (
    InstrumentTradingState,
    TradingSessionState,
)
from infrastructure.sqlite.trading_state_repository import (
    TradingStateRepository,
)


@dataclass(slots=True)
class StartupRecoveryResult:
    recovered_sessions: int = 0
    skipped_sessions: int = 0
    failed_sessions: int = 0


@dataclass(slots=True)
class StartupRecoveryService:
    settings: Settings

    state_repository: (
        TradingStateRepository
    )

    state_service: (
        TradingSessionStateService
    )

    api_usage_repository: object

    runner_registry: (
        WebRunnerRegistry
    )

    polling_interval_seconds: int = 10

    def recover_all(
        self,
    ) -> StartupRecoveryResult:
        result = (
            StartupRecoveryResult()
        )

        states = (
            self.state_repository
            .get_active()
        )

        if not states:
            print(
                "STARTUP RECOVERY: "
                "no active snapshots"
            )

            return result

        print(
            "STARTUP RECOVERY:",
            len(states),
            "active snapshot(s)",
        )

        for state in states:
            try:
                if not self._can_recover(
                    state=state,
                ):
                    result.skipped_sessions += 1

                    continue

                self._recover_one(
                    state=state,
                )

                result.recovered_sessions += 1

            except Exception as error:
                result.failed_sessions += 1

                print(
                    "STARTUP RECOVERY FAILED:",
                    state.session_id,
                    repr(error),
                )

                try:
                    self.api_usage_repository.record(
                        source="runner",
                        operation=(
                            "startup_recovery_failed"
                        ),
                        weight=1,
                    )
                except Exception:
                    pass

        print(
            "STARTUP RECOVERY COMPLETED:",
            "recovered=",
            result.recovered_sessions,
            "skipped=",
            result.skipped_sessions,
            "failed=",
            result.failed_sessions,
        )

        return result

    def _recover_one(
        self,
        state: TradingSessionState,
    ) -> None:
        print(
            "STARTUP RECOVERY BEGIN:",
            state.session_id,
            "mode=",
            state.mode,
            "account=",
            state.broker_account_id,
        )

        config = (
            self._build_config(
                state=state,
            )
        )

        factory = (
            MultiInstrumentTradingSessionFactory(
                settings=self.settings,
            )
        )

        if state.mode == "live":
            context = (
                factory
                .create_live_session(
                    config=config,

                    #
                    # КРИТИЧНО:
                    # старый approximate
                    # position recovery здесь
                    # НЕ запускаем.
                    #
                    recover_positions=False,

                    account_id_override=(
                        state
                        .broker_account_id
                    ),
                )
            )

        elif state.mode == "sandbox":
            context = (
                factory
                .create_sandbox_session(
                    config=config,

                    account_id_override=(
                        state
                        .broker_account_id
                    ),

                    available_cash_override=(
                        state
                        .available_cash
                        + state
                        .reserved_cash
                    ),

                    #
                    # Не пополняем песочницу
                    # повторно после рестарта.
                    #
                    pay_in=False,
                )
            )

        else:
            raise RuntimeError(
                "Unsupported snapshot mode: "
                f"{state.mode}"
            )

        #
        # 1.
        # Восстанавливаем точный
        # GridEngine snapshot:
        #
        # - levels;
        # - trailing;
        # - positions;
        # - broker order ids;
        # - reservations;
        # - PnL;
        # - initial deposit.
        #
        restored_state = (
            self.state_service
            .restore(
                context=context,
                session_id=(
                    state.session_id
                ),
            )
        )

        if restored_state is None:
            raise RuntimeError(
                "Snapshot disappeared "
                "during recovery"
            )

        #
        # 2.
        # BEFORE FIRST PRICE TICK.
        #
        # Проверяем сохранённые заявки.
        #
        # Если заявка была исполнена,
        # пока EXE был выключен,
        # poll_executions() превратит
        # её в TradeExecutedEvent.
        #
        executed_events = (
            context
            .session
            .poll_executions()
        )

        if executed_events:
            print(
                "STARTUP OFFLINE EXECUTIONS:",
                state.session_id,
                len(executed_events),
            )

        #
        # После обработки offline fills
        # сразу переписываем snapshot.
        #
        self.state_service.save(
            context=context,

            session_id=(
                state.session_id
            ),

            trading_account_id=(
                state
                .trading_account_id
            ),

            status="RECOVERY",
        )

        #
        # 3.
        # Создаём runner только ПОСЛЕ
        # восстановления и первичной
        # проверки исполнений.
        #
        runner = WebRunnerService(
            context=context,

            api_usage_repository=(
                self
                .api_usage_repository
            ),

            polling_interval_seconds=(
                self
                .polling_interval_seconds
            ),

            state_service=(
                self.state_service
            ),

            session_id=(
                state.session_id
            ),

            trading_account_id=(
                state
                .trading_account_id
            ),
        )

        self.runner_registry.start(
            runner=runner,
        )

        try:
            self.api_usage_repository.record(
                source="runner",
                operation=(
                    "startup_recovered"
                ),
                weight=1,
            )
        except Exception:
            pass

        print(
            "STARTUP RECOVERY RUNNING:",
            state.session_id,
        )

    def _can_recover(
        self,
        state: TradingSessionState,
    ) -> bool:
        current_mode = (
            str(
                self.settings
                .trading_mode
            )
            .lower()
        )

        snapshot_mode = (
            str(
                state.mode
            )
            .lower()
        )

        #
        # Нельзя неожиданно поднять
        # live-сессию, если сервер
        # сейчас запущен в sandbox.
        #
        if (
            snapshot_mode
            != current_mode
        ):
            print(
                "STARTUP RECOVERY SKIPPED:",
                state.session_id,
                "snapshot_mode=",
                snapshot_mode,
                "current_mode=",
                current_mode,
            )

            return False

        if snapshot_mode == "live":
            if not (
                self.settings
                .live_trading_enabled
            ):
                print(
                    "STARTUP LIVE RECOVERY "
                    "SKIPPED: "
                    "LIVE_TRADING_ENABLED=0"
                )

                return False

            configured_account = (
                self.settings
                .tinvest_live_account_id
            )

            if (
                configured_account
                != state
                .broker_account_id
            ):
                raise RuntimeError(
                    "Live account mismatch: "
                    f"snapshot="
                    f"{state.broker_account_id}, "
                    f"configured="
                    f"{configured_account}"
                )

        if not state.instruments:
            print(
                "STARTUP RECOVERY SKIPPED:",
                state.session_id,
                "no instruments",
            )

            return False

        return True

    def _build_config(
        self,
        state: TradingSessionState,
    ) -> MultiInstrumentSessionConfig:
        instruments = [
            self._build_instrument_config(
                state=instrument,
            )
            for instrument
            in state.instruments
        ]

        return (
            MultiInstrumentSessionConfig(
                instruments=instruments,

                #
                # При recovery это значение
                # не используется для
                # повторного пополнения.
                #
                sandbox_deposit=(
                    state.initial_deposit
                    or (
                        state
                        .available_cash
                        + state
                        .reserved_cash
                    )
                ),
            )
        )

    def _build_instrument_config(
        self,
        state: InstrumentTradingState,
    ) -> InstrumentConfig:
        config = (
            state.grid_config
        )

        if config is None:
            #
            # Старые snapshot schema.
            #
            quantity = 1

            if state.open_positions:
                quantity = max(
                    1,
                    state
                    .open_positions[0]
                    .quantity,
                )

            return InstrumentConfig(
                ticker=(
                    state.ticker
                ),

                levels_count=(
                    len(
                        state.levels
                    )
                ),

                quantity=(
                    quantity
                ),
            )

        return InstrumentConfig(
            ticker=(
                state.ticker
            ),

            levels_count=(
                len(
                    state.levels
                )
            ),

            quantity=(
                config.quantity
            ),

            entry_rebound_percent=(
                config
                .entry_rebound_percent
            ),

            entry_limit_offset_percent=(
                config
                .entry_limit_offset_percent
            ),

            exit_limit_offset_percent=(
                config
                .exit_limit_offset_percent
            ),

            trailing_percent=(
                config
                .trailing_percent
            ),

            min_profit_percent=(
                config
                .min_profit_percent
            ),

            take_profit_buffer_percent=(
                config
                .take_profit_buffer_percent
            ),

            min_open_positions_for_compensation=(
                config
                .min_open_positions_for_compensation
            ),

            compensation_multiplier=(
                config
                .compensation_multiplier
            ),
        )
