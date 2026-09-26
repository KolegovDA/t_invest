from __future__ import annotations

from dataclasses import dataclass

from broker.live_order_manager import (
    LiveOrderManager,
    LiveOrderRecord,
)
from domain.commands import (
    PlaceBuyLimitCommand,
    PlaceSellLimitCommand,
)
from domain.enums import (
    GridLevelStatus,
)
from domain.order_execution import (
    BrokerActiveOrder,
    PlacedOrder,
)
from strategy.grid_engine import (
    GridEngine,
    GridLevel,
)


@dataclass(slots=True)
class OrderReconcileResult:
    instrument_id: str

    adopted_orders: int = 0

    reverted_entry_levels: int = 0

    reverted_exit_levels: int = 0

    unknown_broker_orders: int = 0

    @property
    def has_changes(
        self,
    ) -> bool:
        return bool(
            self.adopted_orders
            or self
            .reverted_entry_levels
            or self
            .reverted_exit_levels
            or self
            .unknown_broker_orders
        )


@dataclass(slots=True)
class BrokerOrderReconciler:
    """
    Сверка фантомных ORDER_PLACED
    уровней с реальными заявками брокера.

    Инцидент 2026-09-11: брокер отменил
    неисполненные заявки, локальный трекер
    о них уже не знал, уровни навсегда
    остались ORDER_PLACED и заблокировали
    входы/выходы по всем инструментам.

    Правила на каждый уровень
    в статусе ORDER_PLACED:

    1. Заявка отслеживается в
       LiveOrderManager — ничего не делаем.

    2. У брокера есть неотслеживаемая
       заявка того же направления —
       усыновляем её в трекер.

    3. Заявки нет нигде — откатываем:
       BUY → WAITING_PRICE,
       SELL → POSITION_OPENED
       (SELL перевыставится на
       следующем тике).
    """

    def reconcile_instrument(
        self,
        engine: GridEngine,
        manager: LiveOrderManager,
        broker_orders: list[
            BrokerActiveOrder
        ],
    ) -> OrderReconcileResult:
        result = (
            OrderReconcileResult(
                instrument_id=(
                    engine
                    .instrument_id
                ),
            )
        )

        tracked_levels = {
            (
                record
                .command
                .level_index,

                self._command_side(
                    record
                ),
            )

            for record
            in (
                manager
                .active_orders
                .values()
            )
        }

        candidates = [
            order

            for order
            in broker_orders

            if (
                order
                .instrument_id
                == engine
                .instrument_id

                and order.order_id
                not in (
                    manager
                    .active_orders
                )
            )
        ]

        for level in engine.levels:
            if (
                level.status
                != GridLevelStatus
                .ORDER_PLACED
            ):
                continue

            side = (
                self
                ._level_pending_side(
                    engine=engine,

                    level=level,
                )
            )

            if side is None:
                #
                # Фантом без позиции:
                # заявки быть не должно.
                #
                self._revert_entry_level(
                    engine=engine,
                    manager=manager,
                    level=level,
                )

                result\
                    .reverted_entry_levels += 1

                continue

            if (
                (
                    level.index,
                    side,
                )

                in tracked_levels
            ):
                continue

            match = (
                self
                ._pop_candidate(
                    candidates=(
                        candidates
                    ),

                    side=side,
                )
            )

            if match is not None:
                self._adopt_order(
                    manager=manager,
                    engine=engine,
                    level=level,
                    side=side,
                    broker_order=(
                        match
                    ),
                )

                result\
                    .adopted_orders += 1

                continue

            if side == "SELL":
                level.status = (
                    GridLevelStatus
                    .POSITION_OPENED
                )

                result\
                    .reverted_exit_levels += 1

            else:
                self._revert_entry_level(
                    engine=engine,
                    manager=manager,
                    level=level,
                )

                result\
                    .reverted_entry_levels += 1

        result\
            .unknown_broker_orders = (
                len(candidates)
            )

        return result

    def _revert_entry_level(
        self,
        engine: GridEngine,
        manager: LiveOrderManager,
        level: GridLevel,
    ) -> None:
        level.status = (
            GridLevelStatus
            .WAITING_PRICE
        )

        level.trailing_entry = (
            None
        )

        trade_capital_service = (
            manager
            .trade_capital_service
        )

        if (
            trade_capital_service
            is not None
        ):
            #
            # BUY не состоится:
            # деньги снова доступны.
            #
            trade_capital_service\
                .reservation_manager\
                .release(
                    instrument_id=(
                        engine
                        .instrument_id
                    ),

                    level_index=(
                        level.index
                    ),
                )

    def _adopt_order(
        self,
        manager: LiveOrderManager,
        engine: GridEngine,
        level: GridLevel,
        side: str,
        broker_order: (
            BrokerActiveOrder
        ),
    ) -> None:
        if side == "SELL":
            command = (
                PlaceSellLimitCommand(
                    instrument_id=(
                        engine
                        .instrument_id
                    ),

                    level_index=(
                        level.index
                    ),

                    quantity=(
                        broker_order
                        .quantity_lots
                    ),

                    price=(
                        broker_order
                        .price
                    ),
                )
            )

        else:
            command = (
                PlaceBuyLimitCommand(
                    instrument_id=(
                        engine
                        .instrument_id
                    ),

                    level_index=(
                        level.index
                    ),

                    quantity=(
                        broker_order
                        .quantity_lots
                    ),

                    price=(
                        broker_order
                        .price
                    ),
                )
            )

        manager\
            .active_orders[
                broker_order
                .order_id
            ] = LiveOrderRecord(
                command=(
                    command
                ),

                placed_order=(
                    PlacedOrder(
                        order_id=(
                            broker_order
                            .order_id
                        ),

                        request_id=(
                            broker_order
                            .order_id
                        ),
                    )
                ),
            )

        print(
            "BROKER ORDER ADOPTED:",
            engine.instrument_id,
            "level=",
            level.index,
            "side=",
            side,
            "order_id=",
            broker_order.order_id,
        )

    @staticmethod
    def _level_pending_side(
        engine: GridEngine,
        level: GridLevel,
    ) -> str | None:
        #
        # trailing_entry != None —
        # ждём BUY.
        #
        # trailing_entry is None
        # и есть позиция — ждём SELL.
        #
        if (
            level.trailing_entry
            is not None
        ):
            return "BUY"

        if (
            level.index
            in engine.open_positions
        ):
            return "SELL"

        return None

    @staticmethod
    def _pop_candidate(
        candidates: list[
            BrokerActiveOrder
        ],
        side: str,
    ) -> (
        BrokerActiveOrder | None
    ):
        for (
            index,
            order,
        ) in enumerate(
            candidates,
        ):
            if (
                order.direction
                == side
            ):
                return (
                    candidates
                    .pop(index)
                )

        return None

    @staticmethod
    def _command_side(
        record: LiveOrderRecord,
    ) -> str:
        command = (
            record.command
        )

        if isinstance(
            command,
            PlaceBuyLimitCommand,
        ):
            return "BUY"

        if isinstance(
            command,
            PlaceSellLimitCommand,
        ):
            return "SELL"

        return "SELL_ALL"
