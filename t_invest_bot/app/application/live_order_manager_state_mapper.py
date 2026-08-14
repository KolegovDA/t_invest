from __future__ import annotations

from broker.live_order_manager import (
    LiveOrderManager,
    LiveOrderRecord,
)
from domain.commands import (
    PlaceBuyLimitCommand,
    PlaceSellAllLimitCommand,
    PlaceSellLimitCommand,
)
from domain.order_execution import (
    PlacedOrder,
)
from domain.trading_state import (
    BrokerOrderState,
)


class LiveOrderManagerStateMapper:
    def to_states(
        self,
        ticker: str,
        manager: LiveOrderManager,
    ) -> list[BrokerOrderState]:
        result: list[
            BrokerOrderState
        ] = []

        for (
            broker_order_id,
            record,
        ) in manager.active_orders.items():
            command = record.command

            if isinstance(
                command,
                PlaceBuyLimitCommand,
            ):
                side = "BUY"

                level_index = (
                    command.level_index
                )

            elif isinstance(
                command,
                PlaceSellLimitCommand,
            ):
                side = "SELL"

                level_index = (
                    command.level_index
                )

            elif isinstance(
                command,
                PlaceSellAllLimitCommand,
            ):
                side = "SELL_ALL"

                level_index = None

            else:
                continue

            result.append(
                BrokerOrderState(
                    broker_order_id=(
                        broker_order_id
                    ),
                    request_id=(
                        record
                        .placed_order
                        .request_id
                    ),
                    instrument_uid=(
                        command.instrument_id
                    ),
                    ticker=ticker,
                    level_index=(
                        level_index
                    ),
                    side=side,
                    quantity=(
                        command.quantity
                    ),
                    limit_price=(
                        command.price
                    ),
                    status="ACTIVE",
                    lots_requested=(
                        command.quantity
                    ),
                    lots_executed=0,
                    executed_price=None,
                )
            )

        return result

    def restore(
        self,
        manager: LiveOrderManager,
        states: list[
            BrokerOrderState
        ],
    ) -> None:
        #
        # После создания новой сессии
        # in-memory список пуст.
        #
        manager.active_orders.clear()

        for state in states:
            command = (
                self._restore_command(
                    state=state,
                )
            )

            if command is None:
                continue

            placed_order = (
                PlacedOrder(
                    order_id=(
                        state
                        .broker_order_id
                    ),
                    request_id=(
                        state
                        .request_id
                        or state
                        .broker_order_id
                    ),
                )
            )

            manager.active_orders[
                state.broker_order_id
            ] = LiveOrderRecord(
                command=command,
                placed_order=(
                    placed_order
                ),
            )

    def _restore_command(
        self,
        state: BrokerOrderState,
    ):
        if state.side == "BUY":
            if state.level_index is None:
                return None

            return PlaceBuyLimitCommand(
                instrument_id=(
                    state.instrument_uid
                ),
                level_index=(
                    state.level_index
                ),
                quantity=(
                    state.quantity
                ),
                price=(
                    state.limit_price
                ),
            )

        if state.side == "SELL":
            if state.level_index is None:
                return None

            return PlaceSellLimitCommand(
                instrument_id=(
                    state.instrument_uid
                ),
                level_index=(
                    state.level_index
                ),
                quantity=(
                    state.quantity
                ),
                price=(
                    state.limit_price
                ),
            )

        if state.side == "SELL_ALL":
            return (
                PlaceSellAllLimitCommand(
                    instrument_id=(
                        state.instrument_uid
                    ),
                    quantity=(
                        state.quantity
                    ),
                    price=(
                        state.limit_price
                    ),
                    reason=(
                        "RECOVERED_"
                        "COMPENSATION_ORDER"
                    ),
                )
            )

        return None
