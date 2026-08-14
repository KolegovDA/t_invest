from __future__ import annotations

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
    GridLevelState,
    InstrumentTradingState,
    OpenPositionState,
)
from strategy.grid_engine import (
    GridEngine,
)
from strategy.trailing_engine import (
    TrailingEntryState,
    TrailingExitState,
)


class GridEngineStateMapper:
    def to_state(
        self,
        ticker: str,
        engine: GridEngine,
        current_price: Decimal | None = None,
        live_order_manager: (
            LiveOrderManager | None
        ) = None,
    ) -> InstrumentTradingState:
        levels: list[
            GridLevelState
        ] = []

        #
        # Сохраняем состояние
        # всех уровней сетки.
        #
        for level in engine.levels:
            trailing_entry = (
                level.trailing_entry
            )

            levels.append(
                GridLevelState(
                    level_index=(
                        level.index
                    ),
                    level_price=(
                        level.price
                    ),
                    status=(
                        self._enum_value(
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
            )

        positions: list[
            OpenPositionState
        ] = []

        #
        # Сохраняем все открытые
        # позиции GridEngine.
        #
        for position in (
            engine
            .open_positions
            .values()
        ):
            trailing_exit = (
                position.trailing_exit
            )

            positions.append(
                OpenPositionState(
                    level_index=(
                        position
                        .level_index
                    ),
                    entry_price=(
                        position
                        .entry_price
                    ),
                    quantity=(
                        position.quantity
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
                )
            )

        #
        # Сохраняем активные заявки,
        # которые уже существуют
        # у брокера.
        #
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

        return InstrumentTradingState(
            ticker=ticker,

            instrument_uid=(
                engine.instrument_id
            ),

            current_price=(
                current_price
            ),

            realized_profit=(
                engine.realized_profit
            ),

            levels=levels,

            open_positions=(
                positions
            ),

            active_orders=(
                active_orders
            ),
        )

    def restore(
        self,
        engine: GridEngine,
        state: InstrumentTradingState,
    ) -> None:
        #
        # Защита от случайного
        # восстановления snapshot
        # другого инструмента.
        #
        if (
            engine.instrument_id
            != state.instrument_uid
        ):
            raise ValueError(
                "Instrument mismatch: "
                f"{engine.instrument_id} != "
                f"{state.instrument_uid}"
            )

        state_levels = {
            item.level_index: item
            for item
            in state.levels
        }

        #
        # Новый GridEngine после
        # рестарта должен получить
        # позиции только из snapshot.
        #
        engine.open_positions.clear()

        #
        # Возвращаем накопленную
        # реализованную прибыль.
        #
        engine.realized_profit = (
            state.realized_profit
        )

        #
        # Восстанавливаем уровни
        # сетки и entry trailing.
        #
        for level in engine.levels:
            saved_level = (
                state_levels.get(
                    level.index
                )
            )

            if (
                saved_level
                is None
            ):
                continue

            #
            # Не импортируем enum
            # отдельно.
            #
            # Берём его реальный тип
            # из GridLevel.
            #
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
                level.trailing_entry = None

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

        #
        # Восстанавливаем открытые
        # позиции.
        #
        for saved_position in (
            state.open_positions
        ):
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
                )
            )

            #
            # Если trailing exit
            # уже был активирован
            # до рестарта, полностью
            # восстанавливаем его.
            #
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

    def restore_with_orders(
        self,
        engine: GridEngine,
        state: InstrumentTradingState,
        live_order_manager: (
            LiveOrderManager | None
        ),
    ) -> None:
        """
        Полное восстановление
        состояния инструмента.

        Восстанавливает:

        - уровни GridEngine;
        - entry trailing;
        - открытые позиции;
        - exit trailing;
        - realized profit;
        - активные broker orders.
        """

        #
        # Сначала GridEngine.
        #
        self.restore(
            engine=engine,
            state=state,
        )

        #
        # Sandbox или тестовый
        # сценарий может не иметь
        # LiveOrderManager.
        #
        if (
            live_order_manager
            is None
        ):
            return

        #
        # Затем возвращаем уже
        # существующие заявки брокера
        # в LiveOrderManager.
        #
        LiveOrderManagerStateMapper()\
            .restore(
                manager=(
                    live_order_manager
                ),
                states=(
                    state.active_orders
                ),
            )

    @staticmethod
    def _enum_value(
        value,
    ) -> str:
        """
        Безопасно преобразует enum
        состояния уровня в строку
        для JSON snapshot.
        """

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
