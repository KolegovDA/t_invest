from __future__ import annotations

from dataclasses import (
    dataclass,
    field,
)
from decimal import Decimal
from datetime import datetime, timezone

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
from infrastructure.tinvest.last_price_provider import OrderBookQuote
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

    cycle_price_points: list[dict] = field(default_factory=list)

    def on_price(
        self,
        price: Decimal,

        buy_reference_price: (
            Decimal | None
        ) = None,

        sell_reference_price: (
            Decimal | None
        ) = None,
        order_book: OrderBookQuote | None = None,
    ) -> list[
        PlacedOrder
    ]:
        if order_book is not None and order_book.enforce_depth:
            buy_reference_price = order_book.execution_price("BUY", self.grid_engine.config.quantity)
            sell_quantity = max((position.quantity for position in self.grid_engine.open_positions.values()), default=1)
            sell_reference_price = order_book.execution_price("SELL", sell_quantity)
            if buy_reference_price is None:
                buy_reference_price = Decimal("0")
            if sell_reference_price is None:
                sell_reference_price = Decimal("0")
        if self.grid_engine.open_positions:
            self.cycle_price_points.append({"time": datetime.now(timezone.utc).isoformat(), "price": str(price)})
        commands = (
            self.grid_engine
            .on_price(
                current_price=(
                    price
                ),

                buy_reference_price=(
                    buy_reference_price
                ),

                sell_reference_price=(
                    sell_reference_price
                ),
            )
        )

        if order_book is not None and order_book.enforce_depth:
            accepted = []
            rejected = []
            for command in commands:
                if isinstance(command, (PlaceBuyLimitCommand, PlaceSellLimitCommand, PlaceSellAllLimitCommand)):
                    side = "BUY" if isinstance(command, PlaceBuyLimitCommand) else "SELL"
                    if order_book.execution_price(side, command.quantity, command.price) is None:
                        rejected.append(command)
                        continue
                accepted.append(command)
            self._revert_levels_for_dropped_commands(rejected)
            commands = accepted
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

        dropped_commands = (
            self
            .live_order_manager
            .last_dropped_commands
        )

        if dropped_commands:
            #
            # Движок уже перевёл уровни
            # в ORDER_PLACED, но заявки
            # брокеру не ушли — откатываем,
            # иначе уровень зависнет
            # навсегда.
            #
            self._revert_levels_for_dropped_commands(
                commands=(
                    dropped_commands
                ),
            )

        return placed_orders

    def _revert_levels_for_dropped_commands(
        self,
        commands: list,
    ) -> None:
        for command in commands:
            if isinstance(
                command,
                PlaceBuyLimitCommand,
            ):
                level = (
                    self
                    .grid_engine
                    ._get_level_by_index(
                        command
                        .level_index
                    )
                )

                if (
                    level is not None
                    and level.status
                    == GridLevelStatus
                    .ORDER_PLACED
                ):
                    level.status = (
                        GridLevelStatus
                        .WAITING_PRICE
                    )

                    level.trailing_entry = (
                        None
                    )

                print(
                    "BUY ORDER DROPPED, "
                    "LEVEL REVERTED:",
                    command.instrument_id,
                    "level=",
                    command.level_index,
                )

                continue

            if isinstance(
                command,
                PlaceSellLimitCommand,
            ):
                level = (
                    self
                    .grid_engine
                    ._get_level_by_index(
                        command
                        .level_index
                    )
                )

                if (
                    level is not None
                    and level.status
                    == GridLevelStatus
                    .ORDER_PLACED
                ):
                    if (
                        command
                        .level_index
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
                    "SELL ORDER DROPPED, "
                    "LEVEL REVERTED:",
                    command.instrument_id,
                    "level=",
                    command.level_index,
                )

                continue

            if isinstance(
                command,
                PlaceSellAllLimitCommand,
            ):
                #
                # Компенсация не отправлена:
                # разрешаем повторную попытку.
                #
                risk_manager = (
                    self
                    .grid_engine
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
                    "SELL ALL ORDER DROPPED:",
                    command.instrument_id,
                )

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

            closed_position = (
                self.grid_engine.open_positions.get(event.level_index)
                if event.side == "SELL" else None
            )
            had_positions = bool(self.grid_engine.open_positions)
            self.grid_engine\
                .on_trade_executed(
                    event=event,
                )
            if event.side == "BUY" and not had_positions:
                self.cycle_price_points = [{"time": datetime.now(timezone.utc).isoformat(), "price": str(event.price)}]
            if event.side == "SELL" and not self.grid_engine.open_positions and self.grid_engine.completed_cycles:
                self.cycle_price_points.append({"time": datetime.now(timezone.utc).isoformat(), "price": str(event.price)})
                self.grid_engine.completed_cycles[-1]["price_points"] = list(self.cycle_price_points)
                self.cycle_price_points.clear()

            if (
                self.trade_event_handler
                is not None
            ):
                self\
                    .trade_event_handler\
                    .handle(
                        event=event,
                        closed_position=closed_position,
                    )

            if event.side == "SELL" and not self.grid_engine.open_positions and self.grid_engine.completed_cycles:
                self.grid_engine.completed_cycles[-1]["events_until"] = datetime.now(timezone.utc).isoformat()

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
