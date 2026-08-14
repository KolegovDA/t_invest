from __future__ import annotations

from dataclasses import (
    dataclass,
    field,
)
from typing import Protocol

from broker.live_order_manager import (
    LiveOrderManager,
    LiveOrderRecord,
)
from domain.order_state import (
    OrderExecutionState,
)


class OrderStateProvider(
    Protocol
):
    def get_order_state(
        self,
        account_id: str,
        order_id: str,
    ) -> OrderExecutionState:
        pass


@dataclass(slots=True)
class ExecutedOrder:
    order_record: LiveOrderRecord
    execution_state: OrderExecutionState


@dataclass(slots=True)
class TerminalOrder:
    order_record: LiveOrderRecord
    execution_state: OrderExecutionState


@dataclass(slots=True)
class OrderPollResult:
    executed_orders: list[
        ExecutedOrder
    ] = field(
        default_factory=list
    )

    terminal_orders: list[
        TerminalOrder
    ] = field(
        default_factory=list
    )


@dataclass(slots=True)
class OrderStateTracker:
    account_id: str

    live_order_manager: (
        LiveOrderManager
    )

    order_state_provider: (
        OrderStateProvider
    )

    executed_orders: list[
        ExecutedOrder
    ] = field(
        default_factory=list
    )

    terminal_orders: list[
        TerminalOrder
    ] = field(
        default_factory=list
    )

    def poll(
        self,
    ) -> OrderPollResult:
        result = (
            OrderPollResult()
        )

        for (
            order_id,
            order_record,
        ) in list(
            self
            .live_order_manager
            .active_orders
            .items()
        ):
            state = (
                self
                .order_state_provider
                .get_order_state(
                    account_id=(
                        self.account_id
                    ),
                    order_id=(
                        order_id
                    ),
                )
            )

            if state.is_executed:
                executed_order = (
                    ExecutedOrder(
                        order_record=(
                            order_record
                        ),
                        execution_state=(
                            state
                        ),
                    )
                )

                result\
                    .executed_orders\
                    .append(
                        executed_order
                    )

                self\
                    .executed_orders\
                    .append(
                        executed_order
                    )

                self\
                    .live_order_manager\
                    .active_orders\
                    .pop(
                        order_id,
                        None,
                    )

                continue

            if (
                state
                .is_terminal_without_execution
            ):
                terminal_order = (
                    TerminalOrder(
                        order_record=(
                            order_record
                        ),
                        execution_state=(
                            state
                        ),
                    )
                )

                result\
                    .terminal_orders\
                    .append(
                        terminal_order
                    )

                self\
                    .terminal_orders\
                    .append(
                        terminal_order
                    )

                self\
                    .live_order_manager\
                    .active_orders\
                    .pop(
                        order_id,
                        None,
                    )

        return result
