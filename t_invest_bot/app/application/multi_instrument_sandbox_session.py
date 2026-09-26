from dataclasses import dataclass, field
from decimal import Decimal

from application.sandbox_trading_session import (
    SandboxTradingSession,
)
from broker.broker_order_reconciler import (
    BrokerOrderReconciler,
    OrderReconcileResult,
)
from domain.events import TradeExecutedEvent
from domain.order_execution import (
    BrokerActiveOrder,
    PlacedOrder,
)


@dataclass(slots=True)
class MultiInstrumentSandboxSession:
    sessions: dict[str, SandboxTradingSession] = field(
        default_factory=dict
    )

    def on_price(
        self,
        instrument_id: str,
        price: Decimal,
    ) -> list[PlacedOrder]:
        session = self.sessions[
            instrument_id
        ]

        return session.on_price(
            price=price,
        )

    def poll_executions(
        self,
    ) -> list[TradeExecutedEvent]:
        result: list[
            TradeExecutedEvent
        ] = []

        for session in self.sessions.values():
            result.extend(
                session.poll_executions()
            )

        return result

    def reconcile_broker_orders(
        self,
    ) -> list[
        OrderReconcileResult
    ]:
        """
        Сверка фантомных ORDER_PLACED
        уровней с реальными заявками
        брокера.

        Один вызов get_orders на счёт,
        дальше каждый инструмент
        сверяется отдельно.

        Для sandbox/fake исполнителей
        (нет list_active_orders) —
        пустой результат без вызовов.
        """

        broker_orders = (
            self._load_broker_orders()
        )

        if broker_orders is None:
            return []

        reconciler = (
            BrokerOrderReconciler()
        )

        results: list[
            OrderReconcileResult
        ] = []

        for session in (
            self.sessions.values()
        ):
            result = (
                reconciler
                .reconcile_instrument(
                    engine=(
                        session
                        .grid_engine
                    ),

                    manager=(
                        session
                        .live_order_manager
                    ),

                    broker_orders=(
                        broker_orders
                    ),
                )
            )

            results.append(
                result
            )

        return results

    def _load_broker_orders(
        self,
    ) -> (
        list[BrokerActiveOrder] | None
    ):
        #
        # Все runner-сессии счёта
        # используют один и тот же
        # order_executor, поэтому
        # достаточно одного вызова.
        #
        for session in (
            self.sessions.values()
        ):
            executor = (
                session
                .live_order_manager
                .order_executor
            )

            lister = getattr(
                executor,
                "list_active_orders",
                None,
            )

            if lister is None:
                #
                # Sandbox/fake executor:
                # сверка только для LIVE.
                #
                return None

            return lister(
                account_id=(
                    session
                    .live_order_manager
                    .account_id
                ),
            )

        return None

    def stop(self) -> None:
        for session in self.sessions.values():
            session.stop()
