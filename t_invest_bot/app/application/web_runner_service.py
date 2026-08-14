from __future__ import annotations

from dataclasses import dataclass, field
from datetime import (
    datetime,
    timezone,
)
from decimal import Decimal
from threading import (
    Lock,
    Thread,
)
from time import sleep
from typing import Any

from application.sandbox_session_registry import (
    SandboxSessionRegistry,
    sandbox_session_registry,
)
from application.trading_session_state_service import (
    TradingSessionStateService,
)


@dataclass(slots=True)
class WebRunnerTickResult:
    prices_checked: int = 0
    orders_placed: int = 0
    executions: int = 0


@dataclass(slots=True)
class WebRunnerStatus:
    is_running: bool
    last_tick_at: str | None
    last_error: str | None

    ticks_count: int

    prices_checked_total: int
    orders_placed_total: int
    executions_total: int


@dataclass(slots=True)
class WebRunnerService:
    context: Any
    api_usage_repository: Any

    registry: SandboxSessionRegistry = field(
        default_factory=lambda: (
            sandbox_session_registry
        ),
    )

    polling_interval_seconds: int = 10

    #
    # Persistence 1.1
    #
    # Пока параметры опциональные,
    # чтобы не сломать старые sandbox
    # тесты и вызовы.
    #
    state_service: (
        TradingSessionStateService | None
    ) = None

    session_id: str | None = None

    trading_account_id: str | None = None

    is_running: bool = False

    thread: Thread | None = field(
        default=None,
        init=False,
    )

    last_tick_at: (
        datetime | None
    ) = None

    last_error: str | None = None

    ticks_count: int = 0

    prices_checked_total: int = 0
    orders_placed_total: int = 0
    executions_total: int = 0

    _state_lock: Lock = field(
        default_factory=Lock,
        init=False,
        repr=False,
    )

    def start(self) -> None:
        if self.is_running:
            return

        self.registry.register_multi_session(
            session=(
                self.context.session
            ),
            instrument_ids_by_ticker=(
                self.context
                .instrument_ids_by_ticker
            ),
        )

        self.is_running = True
        self.last_error = None

        #
        # Сохраняем стартовый snapshot
        # ДО запуска рабочего потока.
        #
        # В случае аварии сразу после
        # запуска мы всё равно будем
        # знать, что сессия существовала.
        #
        self._save_state(
            status="RUNNING",
        )

        self.thread = Thread(
            target=self._run_loop,
            daemon=True,
            name=(
                f"trading-runner-"
                f"{self.session_id or 'legacy'}"
            ),
        )

        self.thread.start()

    def stop(self) -> None:
        #
        # Сначала запрещаем новые тики.
        #
        self.is_running = False

        #
        # Важно:
        # состояние сохраняем ДО
        # context.session.stop(),
        # потому что stop() может
        # очистить или отменить часть
        # in-memory состояния.
        #
        self._save_state(
            status="STOPPED",
        )

        if hasattr(
            self.context.session,
            "stop",
        ):
            self.context.session.stop()

        for ticker in list(
            self.context
            .instrument_ids_by_ticker
            .keys()
        ):
            self.registry.unregister(
                ticker=ticker,
            )

    def get_status(
        self,
    ) -> WebRunnerStatus:
        return WebRunnerStatus(
            is_running=self.is_running,

            last_tick_at=(
                self.last_tick_at
                .isoformat()
                if (
                    self.last_tick_at
                    is not None
                )
                else None
            ),

            last_error=(
                self.last_error
            ),

            ticks_count=(
                self.ticks_count
            ),

            prices_checked_total=(
                self
                .prices_checked_total
            ),

            orders_placed_total=(
                self
                .orders_placed_total
            ),

            executions_total=(
                self
                .executions_total
            ),
        )

    def tick_once(
        self,
    ) -> WebRunnerTickResult:
        self.api_usage_repository.record(
            source="runner",
            operation="loop_iteration",
            weight=1,
        )

        result = (
            WebRunnerTickResult()
        )

        api_source = (
            "live"
            if (
                getattr(
                    self.context,
                    "mode",
                    "sandbox",
                )
                == "live"
            )
            else "sandbox"
        )

        for (
            ticker,
            instrument_id,
        ) in (
            self.context
            .instrument_ids_by_ticker
            .items()
        ):
            price = (
                self.context
                .price_provider
                .get_last_price(
                    instrument_uid=(
                        instrument_id
                    ),
                )
            )

            price = Decimal(
                str(price)
            )

            self.api_usage_repository.record(
                source="tinvest",
                operation="get_last_price",
                weight=1,
                ticker=ticker,
            )

            #
            # Для Web UI.
            #
            self.registry.set_current_price(
                ticker=ticker,
                price=price,
            )

            #
            # Для PortfolioManager.
            #
            if hasattr(
                self.context
                .portfolio_manager,
                "update_market_price",
            ):
                self.context\
                    .portfolio_manager\
                    .update_market_price(
                        instrument_id=(
                            instrument_id
                        ),
                        price=price,
                    )

            #
            # Основная стратегия.
            #
            placed_orders = (
                self.context
                .session
                .on_price(
                    instrument_id=(
                        instrument_id
                    ),
                    price=price,
                )
            )

            if placed_orders:
                self.api_usage_repository.record(
                    source=api_source,
                    operation="place_order",
                    weight=len(
                        placed_orders
                    ),
                    ticker=ticker,
                )

            result.prices_checked += 1

            result.orders_placed += (
                len(
                    placed_orders
                )
            )

        #
        # Проверяем состояния уже
        # выставленных заявок.
        #
        executed_events = (
            self.context
            .session
            .poll_executions()
        )

        self.api_usage_repository.record(
            source=api_source,
            operation="poll_executions",
            weight=1,
        )

        if executed_events:
            self.api_usage_repository.record(
                source=api_source,
                operation=(
                    "executed_events"
                ),
                weight=len(
                    executed_events
                ),
            )

        result.executions = len(
            executed_events
        )

        #
        # Счётчики runner.
        #
        self.last_tick_at = (
            datetime.now(
                timezone.utc
            )
        )

        self.last_error = None

        self.ticks_count += 1

        self.prices_checked_total += (
            result.prices_checked
        )

        self.orders_placed_total += (
            result.orders_placed
        )

        self.executions_total += (
            result.executions
        )

        #
        # КЛЮЧЕВОЙ МОМЕНТ 1.1:
        #
        # После полного завершения тика
        # сохраняем атомарный snapshot:
        #
        # - Grid levels;
        # - positions;
        # - trailing;
        # - broker order_id;
        # - reserves;
        # - realized profit.
        #
        self._save_state(
            status="RUNNING",
        )

        return result

    def _run_loop(
        self,
    ) -> None:
        while self.is_running:
            try:
                self.tick_once()

            except Exception as error:
                self.last_error = repr(
                    error
                )

                self.api_usage_repository.record(
                    source="runner",
                    operation="runner_error",
                    weight=1,
                )

                #
                # Сохраняем последнее
                # известное состояние.
                #
                # RECOVERY означает:
                # после рестарта нельзя
                # сразу давать price tick,
                # сначала нужна сверка
                # с брокером.
                #
                self._save_state(
                    status="RECOVERY",
                    suppress_errors=True,
                )

            sleep(
                self.polling_interval_seconds,
            )

    def _save_state(
        self,
        status: str,
        suppress_errors: bool = False,
    ) -> None:
        #
        # Legacy / тестовый runner
        # может работать без persistence.
        #
        if (
            self.state_service
            is None
        ):
            return

        if not self.session_id:
            return

        if not self.trading_account_id:
            return

        #
        # stop() может прийти из Web
        # потока одновременно с tick().
        #
        # Не допускаем параллельной
        # записи snapshot.
        #
        with self._state_lock:
            try:
                self.state_service.save(
                    context=self.context,
                    session_id=(
                        self.session_id
                    ),
                    trading_account_id=(
                        self
                        .trading_account_id
                    ),
                    status=status,
                )

            except Exception as error:
                #
                # Ошибка persistence
                # должна быть видна.
                #
                persistence_error = (
                    "STATE SAVE ERROR: "
                    f"{error!r}"
                )

                print(
                    persistence_error
                )

                if self.last_error is None:
                    self.last_error = (
                        persistence_error
                    )

                else:
                    self.last_error = (
                        f"{self.last_error}; "
                        f"{persistence_error}"
                    )

                try:
                    self.api_usage_repository\
                        .record(
                            source="runner",
                            operation=(
                                "state_save_error"
                            ),
                            weight=1,
                        )
                except Exception:
                    pass

                if not suppress_errors:
                    raise
