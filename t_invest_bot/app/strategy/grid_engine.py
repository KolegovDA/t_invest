from dataclasses import (
    dataclass,
    field,
)
from decimal import Decimal

from domain.commands import (
    PlaceBuyLimitCommand,
    PlaceSellLimitCommand,
    TradingCommand,
)
from domain.enums import (
    GridLevelStatus,
)
from domain.events import (
    TradeExecutedEvent,
)
from domain.positions import (
    OpenLevelPosition,
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


@dataclass(slots=True)
class GridLevel:
    index: int
    price: Decimal

    status: GridLevelStatus = (
        GridLevelStatus
        .WAITING_PRICE
    )

    trailing_entry: (
        TrailingEntryState | None
    ) = None


@dataclass(slots=True)
class GridEngineConfig:
    entry_limit_offset_percent: (
        Decimal
    ) = Decimal("0.15")

    exit_limit_offset_percent: (
        Decimal
    ) = Decimal("0.15")

    entry_rebound_percent: (
        Decimal
    ) = Decimal("0.15")

    trailing_percent: Decimal = (
        Decimal("0.50")
    )

    min_profit_percent: Decimal = (
        Decimal("0.30")
    )

    take_profit_buffer_percent: (
        Decimal
    ) = Decimal("0.15")

    fallback_buy_commission_percent: (
        Decimal
    ) = Decimal("0.30")

    fallback_sell_commission_percent: (
        Decimal
    ) = Decimal("0.30")

    min_open_positions_for_compensation: (
        int
    ) = 5

    compensation_multiplier: (
        Decimal
    ) = Decimal("3")

    quantity: int = 1


@dataclass(slots=True)
class GridEngine:
    instrument_id: str

    levels: list[
        GridLevel
    ]

    config: GridEngineConfig = field(
        default_factory=(
            GridEngineConfig
        )
    )

    trailing_engine: (
        TrailingEngine
    ) = field(
        init=False
    )

    risk_manager: (
        GridRiskManager
    ) = field(
        init=False
    )

    open_positions: dict[
        int,
        OpenLevelPosition,
    ] = field(
        default_factory=dict
    )

    realized_profit: Decimal = (
        Decimal("0")
    )

    #
    # Накопленные фактические
    # комиссии этой сессии.
    #
    total_buy_commission: Decimal = (
        Decimal("0")
    )

    total_sell_commission: Decimal = (
        Decimal("0")
    )

    def __post_init__(
        self,
    ) -> None:
        self.trailing_engine = (
            TrailingEngine(
                entry_rebound_percent=(
                    self.config
                    .entry_rebound_percent
                ),

                trailing_percent=(
                    self.config
                    .trailing_percent
                ),
            )
        )

        self.risk_manager = (
            GridRiskManager(
                instrument_id=(
                    self.instrument_id
                ),

                config=(
                    GridRiskManagerConfig(
                        min_open_positions_for_compensation=(
                            self.config
                            .min_open_positions_for_compensation
                        ),

                        compensation_multiplier=(
                            self.config
                            .compensation_multiplier
                        ),

                        emergency_sell_offset_percent=(
                            self.config
                            .exit_limit_offset_percent
                        ),
                    )
                ),
            )
        )

        self.levels.sort(
            key=lambda level: (
                level.index
            )
        )

    def on_price(
        self,
        current_price: Decimal,
    ) -> list[
        TradingCommand
    ]:
        commands: list[
            TradingCommand
        ] = []

        commands.extend(
            self._process_entries(
                current_price=(
                    current_price
                ),
            )
        )

        commands.extend(
            self._process_exits(
                current_price=(
                    current_price
                ),
            )
        )

        commands.extend(
            self.risk_manager
            .check_compensation_close(
                open_positions=(
                    self.open_positions
                ),

                realized_profit=(
                    self.realized_profit
                ),

                current_price=(
                    current_price
                ),
            )
        )

        return commands

    def on_trade_executed(
        self,
        event: TradeExecutedEvent,
    ) -> list[
        TradingCommand
    ]:
        if (
            event.instrument_id
            != self.instrument_id
        ):
            return []

        level = (
            self
            ._get_level_by_index(
                event.level_index
            )
        )

        if level is None:
            return []

        if (
            event.side
            == "BUY"
        ):
            hard_take_profit_price = (
                self
                ._calculate_hard_take_profit_price(
                    entry_price=(
                        event.price
                    ),
                )
            )

            buy_commission = (
                self
                ._calculate_buy_commission(
                    price=(
                        event.price
                    ),

                    quantity=(
                        event.quantity
                    ),

                    actual_commission=(
                        event.commission
                    ),
                )
            )

            #
            # Для live используем
            # фактическую денежную сумму
            # брокера.
            #
            if (
                event.total_amount
                is not None
                and event.total_amount > 0
            ):
                purchase_cost = (
                    event.total_amount
                    + buy_commission
                )

            else:
                #
                # Sandbox / legacy fallback.
                #
                purchase_cost = (
                    event.price
                    * Decimal(
                        event.quantity
                    )
                    + buy_commission
                )

            self.total_buy_commission += (
                buy_commission
            )

            self.open_positions[
                event.level_index
            ] = OpenLevelPosition(
                level_index=(
                    event.level_index
                ),

                entry_price=(
                    event.price
                ),

                quantity=(
                    event.quantity
                ),

                buy_commission=(
                    buy_commission
                ),

                expected_sell_commission_percent=(
                    self.config
                    .fallback_sell_commission_percent
                ),

                hard_take_profit_price=(
                    hard_take_profit_price
                ),

                purchase_cost=(
                    purchase_cost
                ),
            )

            level.status = (
                GridLevelStatus
                .POSITION_OPENED
            )

            level.trailing_entry = None

        elif (
            event.side
            == "SELL"
        ):
            position = (
                self.open_positions
                .pop(
                    event.level_index,
                    None,
                )
            )

            if position is not None:
                sell_commission = (
                    self
                    ._calculate_sell_commission(
                        price=(
                            event.price
                        ),

                        quantity=(
                            event.quantity
                        ),

                        actual_commission=(
                            event.commission
                        ),
                    )
                )

                self.total_sell_commission += (
                    sell_commission
                )

                if (
                    event.total_amount
                    is not None
                    and event.total_amount > 0
                ):
                    gross_sell_amount = (
                        event
                        .total_amount
                    )

                else:
                    gross_sell_amount = (
                        event.price
                        * Decimal(
                            event.quantity
                        )
                    )

                net_sell_amount = (
                    gross_sell_amount
                    - sell_commission
                )

                if (
                    position.purchase_cost
                    is not None
                ):
                    purchase_cost = (
                        position
                        .purchase_cost
                    )

                else:
                    purchase_cost = (
                        position
                        .entry_price
                        * Decimal(
                            position
                            .quantity
                        )
                        + position
                        .buy_commission
                    )

                profit = (
                    net_sell_amount
                    - purchase_cost
                )

                self.realized_profit += (
                    profit
                )

            level.status = (
                GridLevelStatus
                .WAITING_PRICE
            )

            level.trailing_entry = None

        return []

    def recover_position(
        self,
        quantity: int,
        entry_price: Decimal,
    ) -> None:
        if quantity <= 0:
            return

        if entry_price <= 0:
            raise ValueError(
                "Recovery entry price "
                "must be positive"
            )

        if self.open_positions:
            return

        available_levels = [
            level
            for level
            in self.levels
            if (
                level.index
                not in self
                .open_positions
            )
        ]

        if not available_levels:
            raise RuntimeError(
                "No grid level available "
                "for live position recovery"
            )

        level = min(
            available_levels,

            key=lambda item: abs(
                item.price
                - entry_price
            ),
        )

        hard_take_profit_price = (
            self
            ._calculate_hard_take_profit_price(
                entry_price=(
                    entry_price
                ),
            )
        )

        buy_commission = (
            self
            ._calculate_buy_commission(
                price=(
                    entry_price
                ),

                quantity=(
                    quantity
                ),

                actual_commission=None,
            )
        )

        purchase_cost = (
            entry_price
            * Decimal(quantity)
            + buy_commission
        )

        self.open_positions[
            level.index
        ] = OpenLevelPosition(
            level_index=(
                level.index
            ),

            entry_price=(
                entry_price
            ),

            quantity=(
                quantity
            ),

            buy_commission=(
                buy_commission
            ),

            expected_sell_commission_percent=(
                self.config
                .fallback_sell_commission_percent
            ),

            hard_take_profit_price=(
                hard_take_profit_price
            ),

            purchase_cost=(
                purchase_cost
            ),
        )

        level.status = (
            GridLevelStatus
            .POSITION_OPENED
        )

        level.trailing_entry = None

    def _process_entries(
        self,
        current_price: Decimal,
    ) -> list[
        TradingCommand
    ]:
        commands: list[
            TradingCommand
        ] = []

        active_entry_level_exists = (
            any(
                level.status
                in (
                    GridLevelStatus
                    .TRAILING_ENTRY,

                    GridLevelStatus
                    .ORDER_PLACED,
                )
                for level
                in self.levels
            )
        )

        if not active_entry_level_exists:
            for level in (
                self.levels
            ):
                if (
                    level.status
                    != GridLevelStatus
                    .WAITING_PRICE
                ):
                    continue

                if (
                    current_price
                    <= level.price
                ):
                    level.status = (
                        GridLevelStatus
                        .TRAILING_ENTRY
                    )

                    level.trailing_entry = (
                        TrailingEntryState(
                            level_price=(
                                level.price
                            ),

                            lowest_price=(
                                current_price
                            ),
                        )
                    )

                    break

        for level in (
            self.levels
        ):
            if (
                level.status
                != GridLevelStatus
                .TRAILING_ENTRY
            ):
                continue

            if (
                level.trailing_entry
                is None
            ):
                continue

            level.trailing_entry = (
                self.trailing_engine
                .update_entry(
                    level
                    .trailing_entry,

                    current_price,
                )
            )

            if not (
                level
                .trailing_entry
                .is_confirmed
            ):
                continue

            buy_price = (
                current_price
                * (
                    Decimal("1")
                    + (
                        self.config
                        .entry_limit_offset_percent
                        / Decimal("100")
                    )
                )
            )

            commands.append(
                PlaceBuyLimitCommand(
                    instrument_id=(
                        self.instrument_id
                    ),

                    level_index=(
                        level.index
                    ),

                    quantity=(
                        self.config
                        .quantity
                    ),

                    price=(
                        buy_price
                    ),
                )
            )

            level.status = (
                GridLevelStatus
                .ORDER_PLACED
            )

            break

        return commands

    def _process_exits(
        self,
        current_price: Decimal,
    ) -> list[
        TradingCommand
    ]:
        commands: list[
            TradingCommand
        ] = []

        for (
            level_index,
            position,
        ) in list(
            self
            .open_positions
            .items()
        ):
            level = (
                self
                ._get_level_by_index(
                    level_index
                )
            )

            if level is None:
                continue

            if (
                level.status
                == GridLevelStatus
                .ORDER_PLACED
            ):
                continue

            activation_price = (
                self
                ._calculate_exit_activation_price(
                    hard_take_profit_price=(
                        position
                        .hard_take_profit_price
                    )
                )
            )

            if (
                position.trailing_exit
                is None
            ):
                if (
                    current_price
                    < activation_price
                ):
                    continue

                position.trailing_exit = (
                    TrailingExitState(
                        target_price=(
                            activation_price
                        ),

                        highest_price=(
                            current_price
                        ),
                    )
                )

            position.trailing_exit = (
                self.trailing_engine
                .update_exit(
                    position
                    .trailing_exit,

                    current_price,
                )
            )

            if not (
                position
                .trailing_exit
                .is_confirmed
            ):
                continue

            sell_price = (
                current_price
                * (
                    Decimal("1")
                    - (
                        self.config
                        .exit_limit_offset_percent
                        / Decimal("100")
                    )
                )
            )

            if (
                sell_price
                < position
                .hard_take_profit_price
            ):
                position.trailing_exit = (
                    None
                )

                continue

            commands.append(
                PlaceSellLimitCommand(
                    instrument_id=(
                        self
                        .instrument_id
                    ),

                    level_index=(
                        position
                        .level_index
                    ),

                    quantity=(
                        position.quantity
                    ),

                    price=(
                        sell_price
                    ),
                )
            )

            level.status = (
                GridLevelStatus
                .ORDER_PLACED
            )

        return commands

    def _calculate_exit_activation_price(
        self,
        hard_take_profit_price: Decimal,
    ) -> Decimal:
        trailing_multiplier = (
            Decimal("1")
            - (
                self.config
                .trailing_percent
                / Decimal("100")
            )
        )

        sell_offset_multiplier = (
            Decimal("1")
            - (
                self.config
                .exit_limit_offset_percent
                / Decimal("100")
            )
        )

        combined_multiplier = (
            trailing_multiplier
            * sell_offset_multiplier
        )

        if combined_multiplier <= 0:
            raise ValueError(
                "Invalid trailing/exit "
                "configuration"
            )

        return (
            hard_take_profit_price
            / combined_multiplier
        )

    def _calculate_hard_take_profit_price(
        self,
        entry_price: Decimal,
    ) -> Decimal:
        buy_commission_rate = (
            self.config
            .fallback_buy_commission_percent
            / Decimal("100")
        )

        sell_commission_rate = (
            self.config
            .fallback_sell_commission_percent
            / Decimal("100")
        )

        min_profit_rate = (
            self.config
            .min_profit_percent
            / Decimal("100")
        )

        buffer_rate = (
            self.config
            .take_profit_buffer_percent
            / Decimal("100")
        )

        required_rate = (
            Decimal("1")
            + buy_commission_rate
            + min_profit_rate
            + buffer_rate
        )

        return (
            entry_price
            * required_rate
            / (
                Decimal("1")
                - sell_commission_rate
            )
        )

    def _calculate_buy_commission(
        self,
        price: Decimal,
        quantity: int,
        actual_commission: (
            Decimal | None
        ),
    ) -> Decimal:
        if (
            actual_commission
            is not None
        ):
            return (
                actual_commission
            )

        return (
            price
            * Decimal(quantity)
            * self.config
            .fallback_buy_commission_percent
            / Decimal("100")
        )

    def _calculate_sell_commission(
        self,
        price: Decimal,
        quantity: int,
        actual_commission: (
            Decimal | None
        ),
    ) -> Decimal:
        if (
            actual_commission
            is not None
        ):
            return (
                actual_commission
            )

        return (
            price
            * Decimal(quantity)
            * self.config
            .fallback_sell_commission_percent
            / Decimal("100")
        )

    def _get_level_by_index(
        self,
        level_index: int,
    ) -> GridLevel | None:
        for level in (
            self.levels
        ):
            if (
                level.index
                == level_index
            ):
                return level

        return None
