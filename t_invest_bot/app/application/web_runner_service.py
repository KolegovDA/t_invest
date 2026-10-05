from __future__ import annotations

from dataclasses import dataclass, field
from datetime import (
    datetime,
    timezone,
)
from decimal import Decimal
from domain.commands import PlaceBuyLimitCommand, PlaceSellLimitCommand
from domain.enums import GridLevelStatus
from threading import (
    Lock,
    Thread,
)
from time import sleep
from typing import Any, Callable

from application.broker_position_reconciler import (
    BrokerPositionReconciler,
)
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
    lifecycle_status: str
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
    # Периодическая сверка open_positions
    # с позициями брокера: первый тик
    # и далее раз в час при интервале
    # 10 секунд.
    #
    position_reconcile_interval_ticks: (
        int
    ) = 360

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

    #
    # Журнал сверки с брокером
    # (v1.1 стабилизация).
    #
    reconciliation_journal: (
        Any | None
    ) = None

    session_id: str | None = None

    trading_account_id: str | None = None

    # Fixed capital required by the strategy at LIVE validation/start.
    # It is persisted as TradingSessionState.initial_deposit.
    planned_initial_capital: Decimal | None = None

    # RUNNING or DRAINING. DRAINING does not change GridEngine logic;
    # it only stops the runner when the last open position disappears.
    lifecycle_status: str = "RUNNING"

    on_auto_stopped: (
        Callable[["WebRunnerService"], None] | None
    ) = None

    #
    # Ребаланс авторежима v1.1:
    # после полного закрытия сетки
    # по инструменту — замена на
    # более волатильную акцию и
    # добор активов до лимита.
    #
    auto_rebalance: Any | None = None

    #
    # Журнал операций v1.2:
    # протоколирование выставленных
    # ордеров для истории на Главной.
    #
    operation_log: Any | None = None

    #
    # Комиссия v1.3: при
    # отрицательном ЛК-балансе
    # авторебаланс не запускает
    # новые инструменты
    # (принудительная сушка).
    #
    commission_service: (
        Any | None
    ) = None

    is_running: bool = False

    _had_open_positions: dict = field(
        default_factory=dict,
        init=False,
        repr=False,
    )

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
            status=self.lifecycle_status,
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
            lifecycle_status=self.lifecycle_status,

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

        #
        # Сверка фантомных ORDER_PLACED
        # уровней с реальными заявками
        # брокера ДО новых команд:
        # усыновление живых заявок,
        # откат зависших уровней.
        #
        if self.lifecycle_status == "STOPPING":
            return self._tick_market_stop()
        self._reconcile_broker_orders_safe()

        if (
            self
            .position_reconcile_interval_ticks
            > 0

            and (
                self.ticks_count
                % (
                    self
                    .position_reconcile_interval_ticks
                )
            ) == 0
        ):
            self._reconcile_broker_positions_safe()

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
            #
            # Цены v1.5: mid стакана;
            # покупки — от лучшего
            # ask, продажи — от
            # лучшего bid. Пустой
            # стакан — цена последней
            # сделки.
            #
            quote = (
                self.context
                .price_provider
                .get_order_book_quote(
                    instrument_uid=(
                        instrument_id
                    ),
                )
            )

            price = (
                quote
                .mid_price()
            )

            if price is None:
                price = (
                    quote
                    .last_price
                )

            if price is None:
                price = (
                    self.context
                    .price_provider
                    .get_last_price(
                        instrument_uid=(
                            instrument_id
                        ),
                    )
                )

            buy_reference_price = (
                quote
                .buy_reference_price()
            )

            if (
                buy_reference_price
                is None
            ):
                buy_reference_price = (
                    price
                )

            sell_reference_price = (
                quote
                .sell_reference_price()
            )

            if (
                sell_reference_price
                is None
            ):
                sell_reference_price = (
                    price
                )

            price = Decimal(
                str(price)
            )

            self.api_usage_repository.record(
                source="tinvest",
                operation=(
                    "get_order_book"
                ),
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
            trading_session = getattr(self.context.session, "sessions", {}).get(instrument_id)
            if (
                self.commission_service is not None
                and trading_session is not None
                and not trading_session.grid_engine.open_positions
                and self.commission_service.is_forced_drain()
            ):
                manager = trading_session.live_order_manager
                for order_id, record in list(manager.active_orders.items()):
                    if isinstance(record.command, PlaceBuyLimitCommand):
                        manager.order_executor.cancel_order(manager.account_id, order_id)
                result.prices_checked += 1
                continue

            placed_orders = (
                self.context
                .session
                .on_price(
                    instrument_id=(
                        instrument_id
                    ),

                    price=price,

                    buy_reference_price=(
                        buy_reference_price
                    ),

                    sell_reference_price=(
                        sell_reference_price
                    ),
                    **({"order_book": quote} if quote.enforce_depth else {}),
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

                if (
                    self
                    .operation_log
                    is not None
                ):
                    for order in placed_orders:
                        self\
                            .operation_log\
                            .record_order_placed(
                                trading_account_id=(
                                    self
                                    .trading_account_id
                                ),

                                instrument_id=(
                                    instrument_id
                                ),

                                ticker=(
                                    ticker
                                ),

                                order=(
                                    order
                                ),
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
        # Ребаланс авторежима v1.1:
        # полное закрытие сетки
        # по инструменту.
        #
        self._maybe_auto_rebalance()

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
        #
        # DRAINING / «Сушка»:
        # текущая сетка работает полностью штатно, пока есть хотя бы
        # одна открытая позиция. Закрытые уровни могут покупаться снова,
        # trailing и compensation не меняются.
        #
        # После poll_executions(), если последняя позиция закрылась,
        # сессию завершаем до следующего price tick. context.session.stop()
        # отменит возможные оставшиеся заявки и освободит резерв.
        #
        if (
            self.lifecycle_status == "DRAINING"
            and self._get_open_positions_count() == 0
        ):
            self._complete_drain()
            return result

        self._save_state(
            status=self.lifecycle_status,
        )

        return result

    def request_market_stop(self) -> None:
        if self.lifecycle_status == "STOPPED":
            return
        self.lifecycle_status = "STOPPING"
        self._save_state("STOPPING")

    def _tick_market_stop(self) -> WebRunnerTickResult:
        result = WebRunnerTickResult()
        self.context.session.poll_executions()
        awaiting_broker_orders = False
        for instrument_id, session in self.context.session.sessions.items():
            manager = session.live_order_manager
            executor = manager.order_executor
            for order_id, record in list(manager.active_orders.items()):
                if not isinstance(record.command, PlaceSellLimitCommand) or not record.command.is_market:
                    executor.cancel_order(manager.account_id, order_id)
            session.poll_executions()
            if manager.active_orders:
                continue
            broker_orders = executor.list_active_orders(manager.account_id) if hasattr(executor, "list_active_orders") else []
            matching = [order for order in broker_orders if order.instrument_id == instrument_id]
            if matching:
                awaiting_broker_orders = True
                for order in matching:
                    executor.cancel_order(manager.account_id, order.order_id)
                continue
            for position in list(session.grid_engine.open_positions.values()):
                command = PlaceSellLimitCommand(
                    instrument_id, position.level_index, position.quantity, position.entry_price,
                    is_market=True,
                )
                placed = manager.submit_commands([command])
                if placed:
                    session.grid_engine._get_level_by_index(position.level_index).status = GridLevelStatus.ORDER_PLACED
                    result.orders_placed += len(placed)
                    break
        if not awaiting_broker_orders and self._get_open_positions_count() == 0 and not any(
            session.live_order_manager.active_orders for session in self.context.session.sessions.values()
        ):
            self._complete_drain()
        else:
            self._save_state("STOPPING")
        return result

    def request_drain(self) -> None:
        """
        Перевести runner в режим DRAINING / «Сушка».

        GridEngine продолжает работать без каких-либо ограничений,
        пока существует хотя бы одна открытая позиция.
        Если позиций уже нет, runner завершается сразу.
        """
        if not self.is_running:
            return

        self.lifecycle_status = "DRAINING"

        if self._get_open_positions_count() == 0:
            self._complete_drain()
            return

        self._save_state(
            status="DRAINING",
        )

    def request_resume(self) -> None:
        """
        Отменить сушку: вернуть runner
        в режим RUNNING до закрытия
        последних позиций.

        Работает только пока runner жив
        и находится в DRAINING.
        """
        if not self.is_running:
            return

        if (
            self
            .lifecycle_status
            != "DRAINING"
        ):
            return

        self.lifecycle_status = (
            "RUNNING"
        )

        self._save_state(
            status="RUNNING",
        )

    def _maybe_auto_rebalance(
        self,
    ) -> None:
        service = (
            self
            .auto_rebalance
        )

        if (
            service is None
        ):
            return

        if (
            self
            .lifecycle_status
            == "DRAINING"
        ):
            return

        if (
            self
            .commission_service
            is not None
        ):
            try:
                if (
                    self
                    .commission_service
                    .is_forced_drain()
                ):
                    return

            except Exception:
                return

        sessions = getattr(
            getattr(
                self
                .context,

                "session",
            ),

            "sessions",

            None,
        )

        if not sessions:
            return

        context = (
            self
            .context
        )

        for (
            instrument_id,

            trading_session,
        ) in list(
            sessions
            .items()
        ):
            engine = getattr(
                trading_session,

                "grid_engine",

                None,
            )

            positions = getattr(
                engine,

                "open_positions",

                None,
            )

            count = (
                len(
                    positions
                )

                if (
                    positions
                    is not None
                )

                else 0
            )

            had = (
                self
                ._had_open_positions
                .get(
                    instrument_id,

                    0,
                )
            )

            self\
                ._had_open_positions[
                    instrument_id
                ] = count

            if (
                had <= 0
                or (
                    count
                    != 0
                )
            ):
                continue

            ticker = (
                context
                .tickers_by_instrument_id
                .get(
                    instrument_id
                )
            )

            if not ticker:
                continue

            engine_config = getattr(
                engine,

                "config",

                None,
            )

            closed_quantity = (
                getattr(
                    engine_config,

                    "quantity",

                    1,
                )

                or 1
            )

            try:
                service\
                    .handle_grid_closed(
                        context=(
                            context
                        ),

                        closed_ticker=(
                            ticker
                        ),

                        closed_quantity=(
                            closed_quantity
                        ),

                        api_usage_repository=(
                            self
                            .api_usage_repository
                        ),

                        registry=(
                            self
                            .registry
                        ),
                    )

            except Exception as error:
                self\
                    .last_error = (
                        repr(
                            error
                        )
                    )

            self\
                ._had_open_positions\
                .pop(
                    instrument_id,

                    None,
                )

    def _get_open_positions_count(self) -> int:
        total = 0

        for trading_session in (
            self.context.session.sessions.values()
        ):
            engine = getattr(
                trading_session,
                "grid_engine",
                None,
            )

            if engine is None:
                continue

            total += len(
                getattr(
                    engine,
                    "open_positions",
                    {},
                )
            )

        return total

    def _complete_drain(self) -> None:
        # Запрещаем следующий tick прежде, чем отменять остаточные заявки.
        self.is_running = False
        self.lifecycle_status = "STOPPED"

        if hasattr(
            self.context.session,
            "stop",
        ):
            self.context.session.stop()

        self._save_state(
            status="STOPPED",
            suppress_errors=True,
        )

        for ticker in list(
            self.context.instrument_ids_by_ticker.keys()
        ):
            self.registry.unregister(
                ticker=ticker,
            )

        try:
            self.api_usage_repository.record(
                source="runner",
                operation="runner_drained",
                weight=1,
            )
        except Exception:
            pass

        callback = self.on_auto_stopped
        if callback is not None:
            try:
                callback(self)
            except Exception:
                pass

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
                    status=(
                        self.lifecycle_status
                        if self.lifecycle_status in {"DRAINING", "STOPPING"}
                        else "RECOVERY"
                    ),
                    suppress_errors=True,
                )

            sleep(
                self.polling_interval_seconds,
            )

    def _reconcile_broker_orders_safe(
        self,
    ) -> None:
        reconcile = getattr(
            self.context.session,
            "reconcile_broker_orders",
            None,
        )

        if reconcile is None:
            return

        try:
            results = reconcile()

            for result in results:
                if not result.has_changes:
                    continue

                print(
                    "ORDER RECONCILE:",
                    result.instrument_id,
                    "adopted=",
                    result.adopted_orders,
                    "reverted_entry=",
                    result.reverted_entry_levels,
                    "reverted_exit=",
                    result.reverted_exit_levels,
                    "unknown_broker_orders=",
                    result.unknown_broker_orders,
                )

                try:
                    self\
                        .api_usage_repository\
                        .record(
                            source="runner",
                            operation=(
                                "order_reconcile"
                            ),
                            weight=1,
                        )
                except Exception:
                    pass

                if (
                    self
                    .reconciliation_journal
                    is not None
                ):
                    self\
                        .reconciliation_journal\
                        .record_order_result(
                            trading_account_id=(
                                self
                                .trading_account_id
                            ),

                            result=result,
                        )

        except Exception as error:
            #
            # Ошибка сверки не должна
            # останавливать торговый тик.
            #
            print(
                "BROKER ORDER RECONCILE "
                "ERROR:",
                repr(error),
            )

            if (
                self
                .reconciliation_journal
                is not None
            ):
                self\
                    .reconciliation_journal\
                    .record_error(
                        trading_account_id=(
                            self
                            .trading_account_id
                        ),

                        stage="orders",

                        error=error,
                    )

    def _reconcile_broker_positions_safe(
        self,
    ) -> None:
        position_provider = getattr(
            self.context,
            "position_provider",
            None,
        )

        if position_provider is None:
            return

        try:
            report = (
                BrokerPositionReconciler()
                .reconcile(
                    sessions=(
                        self
                        .context
                        .session
                        .sessions
                    ),

                    account_id=(
                        self
                        .context
                        .account_id
                    ),

                    position_provider=(
                        position_provider
                    ),
                )
            )

            if (
                report.instruments_cleared
                or report
                .mismatch_warnings
            ):
                try:
                    self\
                        .api_usage_repository\
                        .record(
                            source="runner",
                            operation=(
                                "position_reconcile"
                            ),
                            weight=1,
                        )
                except Exception:
                    pass

                if (
                    self
                    .reconciliation_journal
                    is not None
                ):
                    self\
                        .reconciliation_journal\
                        .record_position_report(
                            trading_account_id=(
                                self
                                .trading_account_id
                            ),

                            report=report,
                        )

        except Exception as error:
            #
            # Ошибка сверки не должна
            # останавливать торговый тик.
            #
            print(
                "BROKER POSITION RECONCILE "
                "ERROR:",
                repr(error),
            )

            if (
                self
                .reconciliation_journal
                is not None
            ):
                self\
                    .reconciliation_journal\
                    .record_error(
                        trading_account_id=(
                            self
                            .trading_account_id
                        ),

                        stage="positions",

                        error=error,
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
                    initial_deposit_override=(
                        self.planned_initial_capital
                    ),
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
