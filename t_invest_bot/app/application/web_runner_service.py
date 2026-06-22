from dataclasses import dataclass, field
from decimal import Decimal
from threading import Thread
from time import sleep
from typing import Any

from application.sandbox_session_registry import (
    SandboxSessionRegistry,
    sandbox_session_registry,
)


@dataclass(slots=True)
class WebRunnerTickResult:
    prices_checked: int = 0
    orders_placed: int = 0
    executions: int = 0


@dataclass(slots=True)
class WebRunnerService:
    context: Any
    api_usage_repository: Any
    registry: SandboxSessionRegistry = field(
        default_factory=lambda: sandbox_session_registry
    )
    polling_interval_seconds: int = 10
    is_running: bool = False
    thread: Thread | None = field(default=None, init=False)

    def start(self) -> None:
        if self.is_running:
            return

        self.registry.register_multi_session(
            session=self.context.session,
            instrument_ids_by_ticker=self.context.instrument_ids_by_ticker,
        )

        self.is_running = True

        self.thread = Thread(
            target=self._run_loop,
            daemon=True,
        )
        self.thread.start()

    def stop(self) -> None:
        self.is_running = False

        if hasattr(self.context.session, "stop"):
            self.context.session.stop()

        for ticker in list(
            self.context.instrument_ids_by_ticker.keys()
        ):
            self.registry.unregister(
                ticker=ticker,
            )

    def tick_once(self) -> WebRunnerTickResult:
        self.api_usage_repository.record(
            source="runner",
            operation="loop_iteration",
            weight=1,
        )

        result = WebRunnerTickResult()

        for ticker, instrument_id in (
            self.context.instrument_ids_by_ticker.items()
        ):
            price = self.context.price_provider.get_last_price(
                instrument_uid=instrument_id,
            )

            price = Decimal(str(price))

            self.api_usage_repository.record(
                source="tinvest",
                operation="get_last_price",
                weight=1,
                ticker=ticker,
            )

            self.registry.set_current_price(
                ticker=ticker,
                price=price,
            )

            if hasattr(self.context.portfolio_manager, "update_market_price"):
                self.context.portfolio_manager.update_market_price(
                    instrument_id=instrument_id,
                    price=price,
                )

            placed_orders = self.context.session.on_price(
                instrument_id=instrument_id,
                price=price,
            )

            if placed_orders:
                self.api_usage_repository.record(
                    source="sandbox",
                    operation="place_order",
                    weight=len(placed_orders),
                    ticker=ticker,
                )

            result.prices_checked += 1
            result.orders_placed += len(placed_orders)

        executed_events = self.context.session.poll_executions()

        self.api_usage_repository.record(
            source="sandbox",
            operation="poll_executions",
            weight=1,
        )

        if executed_events:
            self.api_usage_repository.record(
                source="sandbox",
                operation="executed_events",
                weight=len(executed_events),
            )

        result.executions = len(executed_events)

        return result

    def _run_loop(self) -> None:
        while self.is_running:
            self.tick_once()

            sleep(
                self.polling_interval_seconds,
            )
