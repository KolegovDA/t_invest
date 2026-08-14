from __future__ import annotations

from dataclasses import (
    dataclass,
    field,
)
from decimal import Decimal

from application.trade_event_handler import (
    TradeEventHandler,
)
from broker.live_order_manager import (
    LiveOrderManager,
)
from broker.order_execution_event_mapper import (
    OrderExecutionEventMapper,
)
from broker.order_state_tracker import (
    OrderPollResult,
    OrderStateTracker,
    TerminalOrder,
)
from domain.commands import (
    PlaceBuyLimitCommand,
    PlaceSellAllLimitCommand,
    PlaceSellLimitCommand,
)
from domain.enums import (
    GridLevelStatus,
)
from domain.events import (
    TradeExecutedEvent,
)
from domain.order_execution import (
    PlacedOrder,
)
from strategy.grid_engine import (
    GridEngine,
)


@dataclass(slots=True)
class SandboxTradingSession:
    grid_engine: GridEngine

    live_order_manager: (
        LiveOrderManager
    )

    order_state_tracker: (
        OrderStateTracker | None
    ) = None

    execution_event_mapper: (
        OrderExecutionEventMapper
        | None
    ) = None

    trade_event_handler: (
        TradeEventHandler
        | None
    ) = None

    placed_orders: list[
        PlacedOrder
    ] = field(
        default_factory=list
    )

    executed_events: list[
        TradeExecutedEvent
    ] = field(
        default_factory=list
    )

    def on_price(
        self,
        price: Decimal,
    ) -> list[
        PlacedOrder
    ]:
        commands = (
            self.grid_engine
            .on_price(
                current_price=(
                    price
                ),
            )
        )

        if not commands:
            return []

        placed_orders = (
            self
            .live_order_manager
            .submit_commands(
                commands=commands,
            )
        )

        self.placed_orders.extend(
            placed_orders
        )

        return placed_orders

    def poll_executions(
        self,
    ) -> list[
        TradeExecutedEvent
    ]:
        if (
            self.order_state_tracker
            is None
        ):
            return []

        if (
            self.execution_event_mapper
            is None
        ):
            return []

        poll_result = (
            self
            .order_state_tracker
            .poll()
        )

        #
        # Обрабатываем CANCELLED /
        # REJECTED до новых ценовых
        # тиков.
        #
        for terminal_order in (
            poll_result
            .terminal_orders
        ):
            self._handle_terminal_order(
                terminal_order=(
                    terminal_order
                )
            )

        events: list[
            TradeExecutedEvent
        ] = []

        for executed_order in (
            poll_result
            .executed_orders
        ):
            event = (
                self
                .execution_event_mapper
                .map_to_trade_event(
                    executed_order=(
                        executed_order
                    ),
                )
            )

            if (
                event.side
                == "BUY"
            ):
                self\
                    .live_order_manager\
                    .release_reserved_capital_after_buy_execution(
                        instrument_id=(
                            event
                            .instrument_id
                        ),

                        level_index=(
                            event
                            .level_index
                        ),
                    )

            self.grid_engine\
                .on_trade_executed(
                    event=event,
                )

            if (
                self.trade_event_handler
                is not None
            ):
                self\
                    .trade_event_handler\
                    .handle(
                        event=event,
                    )

            self.executed_events.append(
                event
            )

            events.append(
                event
            )

        return events

    def _handle_terminal_order(
        self,
        terminal_order: TerminalOrder,
    ) -> None:
        command = (
            terminal_order
            .order_record
            .command
        )

        status = (
            terminal_order
            .execution_state
            .status
        )

        if isinstance(
            command,
            PlaceBuyLimitCommand,
        ):
            #
            # BUY не состоялся.
            # Деньги снова доступны.
            #
            if (
                self.live_order_manager
                .trade_capital_service
                is not None
            ):
                self\
                    .live_order_manager\
                    .trade_capital_service\
                    .reservation_manager\
                    .release(
                        instrument_id=(
                            command
                            .instrument_id
                        ),

                        level_index=(
                            command
                            .level_index
                        ),
                    )

            level = (
                self.grid_engine
                ._get_level_by_index(
                    command
                    .level_index
                )
            )

            if level is not None:
                level.status = (
                    GridLevelStatus
                    .WAITING_PRICE
                )

                level.trailing_entry = (
                    None
                )

            print(
                "BUY ORDER TERMINAL:",
                command.instrument_id,
                "level=",
                command.level_index,
                "status=",
                status,
            )

            return

        if isinstance(
            command,
            PlaceSellLimitCommand,
        ):
            #
            # SELL не состоялся.
            # Позиция всё ещё наша.
            #
            level = (
                self.grid_engine
                ._get_level_by_index(
                    command
                    .level_index
                )
            )

            if level is not None:
                if (
                    command.level_index
                    in self
                    .grid_engine
                    .open_positions
                ):
                    level.status = (
                        GridLevelStatus
                        .POSITION_OPENED
                    )

                else:
                    level.status = (
                        GridLevelStatus
                        .WAITING_PRICE
                    )

            print(
                "SELL ORDER TERMINAL:",
                command.instrument_id,
                "level=",
                command.level_index,
                "status=",
                status,
            )

            return

        if isinstance(
            command,
            PlaceSellAllLimitCommand,
        ):
            #
            # Компенсационная продажа
            # не произошла.
            #
            risk_manager = (
                self.grid_engine
                .risk_manager
            )

            if hasattr(
                risk_manager,
                "compensation_order_pending",
            ):
                risk_manager\
                    .compensation_order_pending = (
                        False
                    )

            print(
                "SELL ALL ORDER TERMINAL:",
                command.instrument_id,
                "status=",
                status,
            )

    def stop(
        self,
    ) -> None:
        self.live_order_manager\
            .cancel_all_orders()
