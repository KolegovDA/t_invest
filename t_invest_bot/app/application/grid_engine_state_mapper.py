from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from decimal import Decimal

from application.live_order_manager_state_mapper import (
    LiveOrderManagerStateMapper,
)
from broker.live_order_manager import (
    LiveOrderManager,
)
from domain.positions import (
    OpenLevelPosition,
)
from domain.trading_state import (
    GridEngineConfigState,
    GridLevelState,
    InstrumentTradingState,
    OpenPositionState,
)
from strategy.grid_engine import (
    GridEngine,
)
from strategy.grid_risk_manager import (
    GridRiskManager,
    GridRiskManagerConfig,
)
from strategy.trailing_engine import (
    TrailingEngine,
    TrailingEntryState,
    TrailingExitState,
)


class GridEngineStateMapper:
    def to_state(
        self,
        ticker: str,

        engine: GridEngine,

        current_price: (
            Decimal | None
        ) = None,

        live_order_manager: (
            LiveOrderManager | None
        ) = None,
    ) -> InstrumentTradingState:
        levels = [
            self._level_to_state(
                level
            )
            for level
            in engine.levels
        ]

        positions = [
            self._position_to_state(
                position
            )
            for position
            in engine
            .open_positions
            .values()
        ]

        active_orders = []

        if (
            live_order_manager
            is not None
        ):
            active_orders = (
                LiveOrderManagerStateMapper()
                .to_states(
                    ticker=ticker,

                    manager=(
                        live_order_manager
                    ),
                )
            )

        config = (
            engine.config
        )

        grid_config = (
            GridEngineConfigState(
                take_profit_percent=config.take_profit_percent,
                max_take_profit_percent=config.max_take_profit_percent,
                base_order_amount=config.base_order_amount,
                order_amount_multiplier=config.order_amount_multiplier,
                max_order_amount_multiplier=config.max_order_amount_multiplier,
                quantity_step=config.quantity_step,
                min_quantity=config.min_quantity,
                min_order_amount=config.min_order_amount,
                entry_limit_offset_percent=(
                    config
                    .entry_limit_offset_percent
                ),

                exit_limit_offset_percent=(
                    config
                    .exit_limit_offset_percent
                ),

                entry_rebound_percent=(
                    config
                    .entry_rebound_percent
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

                fallback_buy_commission_percent=(
                    config
                    .fallback_buy_commission_percent
                ),

                fallback_sell_commission_percent=(
                    config
                    .fallback_sell_commission_percent
                ),

                min_open_positions_for_compensation=(
                    config
                    .min_open_positions_for_compensation
                ),

                compensation_multiplier=(
                    config
                    .compensation_multiplier
                ),

                quantity=(
                    config.quantity
                ),

                early_close_min_working_time_seconds=(
                    config
                    .early_close_min_working_time_seconds
                ),

                early_close_profit_loss_ratio=(
                    config
                    .early_close_profit_loss_ratio
                ),
            )
        )

        grid_opened_at = (
            engine.grid_opened_at
        )

        return InstrumentTradingState(
            ticker=ticker,

            instrument_uid=(
                engine.instrument_id
            ),

            current_price=(
                current_price
            ),

            realized_profit=(
                engine
                .realized_profit
            ),

            levels=levels,

            open_positions=(
                positions
            ),

            active_orders=(
                active_orders
            ),

            grid_config=(
                grid_config
            ),

            total_buy_commission=Decimal(
                str(
                    getattr(
                        engine,
                        "total_buy_commission",
                        Decimal("0"),
                    )
                )
            ),

            total_sell_commission=Decimal(
                str(
                    getattr(
                        engine,
                        "total_sell_commission",
                        Decimal("0"),
                    )
                )
            ),

            grid_opened_at=(
                grid_opened_at
                .isoformat()
                if (
                    grid_opened_at
                    is not None
                )
                else None
            ),
            completed_cycles=list(engine.completed_cycles),
            cycle_closed_orders=engine.cycle_closed_orders,
            cycle_realized_profit=engine.cycle_realized_profit,
            session_start_price=engine.session_start_price,
            grid_step=engine.grid_step,
        )

    def restore(
        self,
        engine: GridEngine,
        state: InstrumentTradingState,
        use_current_rules: bool = False,
    ) -> None:
        current_config = replace(engine.config)
        current_level_prices = {level.index: level.price for level in engine.levels}

        if (
            engine.instrument_id
            != state.instrument_uid
        ):
            raise ValueError(
                "Instrument mismatch: "
                f"{engine.instrument_id} != "
                f"{state.instrument_uid}"
            )

        if (
            state.grid_config
            is not None
            and not use_current_rules
        ):
            self._restore_config(
                engine=engine,
                state=state,
            )

        state_levels = {
            item.level_index:
                item
            for item
            in state.levels
        }

        if (
            len(state_levels)
            != len(engine.levels)
        ):
            raise RuntimeError(
                "Grid levels count mismatch: "
                f"snapshot={len(state_levels)}, "
                f"engine={len(engine.levels)}"
            )

        if not use_current_rules:
            if state.session_start_price is not None:
                engine.session_start_price = state.session_start_price
            if state.grid_step is not None:
                engine.grid_step = state.grid_step

        engine.open_positions.clear()

        engine.realized_profit = (
            state.realized_profit
        )
        engine.completed_cycles = list(state.completed_cycles)
        engine.cycle_closed_orders = state.cycle_closed_orders if state.open_positions else 0
        engine.cycle_realized_profit = (
            state.cycle_realized_profit if state.open_positions else Decimal("0")
        )

        if hasattr(
            engine,
            "total_buy_commission",
        ):
            engine.total_buy_commission = (
                state
                .total_buy_commission
            )

        if hasattr(
            engine,
            "total_sell_commission",
        ):
            engine.total_sell_commission = (
                state
                .total_sell_commission
            )

        if (
            state.grid_opened_at
            is None
        ):
            engine.grid_opened_at = (
                None
            )

        else:
            engine.grid_opened_at = (
                datetime.fromisoformat(
                    state
                    .grid_opened_at
                )
            )

        for level in (
            engine.levels
        ):
            saved_level = (
                state_levels.get(
                    level.index
                )
            )

            if saved_level is None:
                raise RuntimeError(
                    "Grid level missing "
                    "in snapshot: "
                    f"{level.index}"
                )

            level.price = (
                saved_level
                .level_price
            )

            enum_type = type(
                level.status
            )

            level.status = (
                enum_type(
                    saved_level.status
                )
            )

            if (
                saved_level
                .trailing_entry_lowest_price
                is None
            ):
                level.trailing_entry = (
                    None
                )

            else:
                level.trailing_entry = (
                    TrailingEntryState(
                        level_price=(
                            level.price
                        ),

                        lowest_price=(
                            saved_level
                            .trailing_entry_lowest_price
                        ),
                    )
                )

                level\
                    .trailing_entry\
                    .is_confirmed = (
                        saved_level
                        .trailing_entry_confirmed
                    )

        for saved_position in (
            state.open_positions
        ):
            if (
                saved_position
                .level_index
                not in state_levels
            ):
                raise RuntimeError(
                    "Position references "
                    "unknown level: "
                    f"{saved_position.level_index}"
                )

            position = (
                OpenLevelPosition(
                    level_index=(
                        saved_position
                        .level_index
                    ),

                    entry_price=(
                        saved_position
                        .entry_price
                    ),

                    quantity=(
                        saved_position
                        .quantity
                    ),

                    buy_commission=(
                        saved_position
                        .buy_commission
                    ),

                    expected_sell_commission_percent=(
                        saved_position
                        .expected_sell_commission_percent
                    ),

                    hard_take_profit_price=(
                        saved_position
                        .hard_take_profit_price
                    ),

                    purchase_cost=(
                        saved_position
                        .purchase_cost
                    ),
                )
            )

            if (
                saved_position
                .trailing_exit_highest_price
                is not None
            ):
                target_price = (
                    saved_position
                    .trailing_exit_target_price
                )

                if (
                    target_price
                    is None
                ):
                    target_price = (
                        saved_position
                        .hard_take_profit_price
                    )

                position.trailing_exit = (
                    TrailingExitState(
                        target_price=(
                            target_price
                        ),

                        highest_price=(
                            saved_position
                            .trailing_exit_highest_price
                        ),
                    )
                )

                position\
                    .trailing_exit\
                    .is_confirmed = (
                        saved_position
                        .trailing_exit_confirmed
                    )

            engine.open_positions[
                saved_position
                .level_index
            ] = position

        if use_current_rules:
            engine.config = current_config
            engine.__post_init__()
            grid_step = engine.grid_step
            if grid_step is None:
                raise ValueError("Missing current grid step")
            ordered_levels = {
                order.level_index
                for order in state.active_orders
            }
            for level in engine.levels:
                if (
                    level.index in engine.open_positions
                    or level.index in ordered_levels
                ):
                    continue
                previous_position = engine.open_positions.get(level.index - 1)
                level.price = (
                    previous_position.entry_price - grid_step
                    if previous_position is not None
                    else current_level_prices[level.index]
                )
                if level.trailing_entry is not None:
                    level.trailing_entry.level_price = level.price
                    level.trailing_entry.trigger_price = (
                        engine.trailing_engine._calculate_entry_trigger(
                            highest_price=level.trailing_entry.lowest_price,
                        )
                    )
                    level.trailing_entry.is_confirmed = False

            for position in engine.open_positions.values():
                purchase_cost = position.purchase_cost
                if purchase_cost is None:
                    purchase_cost = (
                        position.entry_price * Decimal(position.quantity)
                        + position.buy_commission
                    )
                    position.purchase_cost = purchase_cost
                gross_amount = purchase_cost - position.buy_commission
                if gross_amount <= 0 or position.entry_price <= 0:
                    raise ValueError("Invalid saved position purchase cost")
                effective_units = gross_amount / position.entry_price
                position.hard_take_profit_price = (
                    engine._calculate_hard_take_profit_price(
                        purchase_cost=purchase_cost,
                        effective_units=effective_units,
                    )
                )
                position.expected_sell_commission_percent = (
                    engine.config.fallback_sell_commission_percent
                )
                if position.trailing_exit is not None:
                    position.trailing_exit.target_price = position.hard_take_profit_price
                    if position.level_index not in ordered_levels:
                        position.trailing_exit.is_confirmed = False

    def restore_with_orders(
        self,
        engine: GridEngine,
        state: InstrumentTradingState,
        live_order_manager: (
            LiveOrderManager | None
        ),
        use_current_rules: bool = False,
    ) -> None:
        self.restore(
            engine=engine,

            state=state,
            use_current_rules=use_current_rules,
        )

        if (
            live_order_manager
            is None
        ):
            return

        LiveOrderManagerStateMapper()\
            .restore(
                manager=(
                    live_order_manager
                ),

                states=(
                    state
                    .active_orders
                ),
            )

    def _restore_config(
        self,
        engine: GridEngine,
        state: InstrumentTradingState,
    ) -> None:
        saved = (
            state.grid_config
        )

        if saved is None:
            return

        engine.config\
            .entry_limit_offset_percent = (
                saved
                .entry_limit_offset_percent
            )

        engine.config\
            .exit_limit_offset_percent = (
                saved
                .exit_limit_offset_percent
            )

        engine.config\
            .entry_rebound_percent = (
                saved
                .entry_rebound_percent
            )

        engine.config\
            .trailing_percent = (
                saved
                .trailing_percent
            )

        engine.config\
            .min_profit_percent = (
                saved
                .min_profit_percent
            )

        engine.config\
            .take_profit_buffer_percent = (
                saved
                .take_profit_buffer_percent
            )

        engine.config\
            .fallback_buy_commission_percent = (
                saved
                .fallback_buy_commission_percent
            )

        engine.config\
            .fallback_sell_commission_percent = (
                saved
                .fallback_sell_commission_percent
            )

        engine.config\
            .min_open_positions_for_compensation = (
                saved
                .min_open_positions_for_compensation
            )

        engine.config\
            .compensation_multiplier = (
                saved
                .compensation_multiplier
            )

        engine.config.quantity = (
            saved.quantity
        )
        engine.config.take_profit_percent = saved.take_profit_percent
        engine.config.max_take_profit_percent = saved.max_take_profit_percent
        engine.config.base_order_amount = saved.base_order_amount
        engine.config.order_amount_multiplier = saved.order_amount_multiplier
        engine.config.max_order_amount_multiplier = saved.max_order_amount_multiplier
        engine.config.quantity_step = saved.quantity_step
        engine.config.min_quantity = saved.min_quantity
        engine.config.min_order_amount = saved.min_order_amount

        engine\
            .config\
            .early_close_min_working_time_seconds = (
                saved
                .early_close_min_working_time_seconds
            )

        engine\
            .config\
            .early_close_profit_loss_ratio = (
                saved
                .early_close_profit_loss_ratio
            )

        engine.trailing_engine = (
            TrailingEngine(
                entry_rebound_percent=(
                    saved
                    .entry_rebound_percent
                ),

                trailing_percent=(
                    saved
                    .trailing_percent
                ),
            )
        )

        engine.risk_manager = (
            GridRiskManager(
                instrument_id=(
                    engine
                    .instrument_id
                ),

                config=(
                    GridRiskManagerConfig(
                        min_open_positions_for_compensation=(
                            saved
                            .min_open_positions_for_compensation
                        ),

                        compensation_multiplier=(
                            saved
                            .compensation_multiplier
                        ),

                        emergency_sell_offset_percent=(
                            saved
                            .exit_limit_offset_percent
                        ),

                        early_close_min_working_time_seconds=(
                            saved
                            .early_close_min_working_time_seconds
                        ),

                        early_close_profit_loss_ratio=(
                            saved
                            .early_close_profit_loss_ratio
                        ),
                    )
                ),
            )
        )

    @staticmethod
    def _level_to_state(
        level,
    ) -> GridLevelState:
        trailing_entry = (
            level.trailing_entry
        )

        return GridLevelState(
            level_index=(
                level.index
            ),

            level_price=(
                level.price
            ),

            status=(
                GridEngineStateMapper
                ._enum_value(
                    level.status
                )
            ),

            trailing_entry_lowest_price=(
                trailing_entry
                .lowest_price
                if (
                    trailing_entry
                    is not None
                )
                else None
            ),

            trailing_entry_confirmed=(
                bool(
                    trailing_entry
                    .is_confirmed
                )
                if (
                    trailing_entry
                    is not None
                )
                else False
            ),
        )

    @staticmethod
    def _position_to_state(
        position,
    ) -> OpenPositionState:
        trailing_exit = (
            position.trailing_exit
        )

        return OpenPositionState(
            level_index=(
                position
                .level_index
            ),

            entry_price=(
                position
                .entry_price
            ),

            quantity=(
                position
                .quantity
            ),

            buy_commission=(
                position
                .buy_commission
            ),

            hard_take_profit_price=(
                position
                .hard_take_profit_price
            ),

            expected_sell_commission_percent=(
                position
                .expected_sell_commission_percent
            ),

            trailing_exit_target_price=(
                trailing_exit
                .target_price
                if (
                    trailing_exit
                    is not None
                )
                else None
            ),

            trailing_exit_highest_price=(
                trailing_exit
                .highest_price
                if (
                    trailing_exit
                    is not None
                )
                else None
            ),

            trailing_exit_confirmed=(
                bool(
                    trailing_exit
                    .is_confirmed
                )
                if (
                    trailing_exit
                    is not None
                )
                else False
            ),

            purchase_cost=(
                position
                .purchase_cost
            ),
        )

    @staticmethod
    def _enum_value(
        value,
    ) -> str:
        raw_value = getattr(
            value,
            "value",
            None,
        )

        if (
            raw_value
            is not None
        ):
            return str(
                raw_value
            )

        return str(
            value
        )
