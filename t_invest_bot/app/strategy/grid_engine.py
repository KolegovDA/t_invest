from __future__ import annotations

from dataclasses import (
    dataclass,
    field,
    replace,
)
from datetime import (
    datetime,
    timezone,
)
from decimal import Decimal, ROUND_FLOOR

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
    #
    # Первый вход:
    # отклонение от цены старта
    # в любую сторону.
    #
    first_entry_activation_percent: (
        Decimal
    ) = Decimal("0.50")

    #
    # BUY trailing под максимумом.
    #
    entry_rebound_percent: Decimal = (
        Decimal("0.15")
    )

    #
    # BUY limit выше рынка.
    #
    entry_limit_offset_percent: Decimal = (
        Decimal("0.15")
    )

    #
    # SELL limit ниже рынка.
    #
    exit_limit_offset_percent: Decimal = (
        Decimal("0.15")
    )

    #
    # SELL trailing под максимумом.
    #
    trailing_percent: Decimal = (
        Decimal("0.15")
    )

    #
    # Минимальная ЧИСТАЯ прибыль.
    #
    min_profit_percent: Decimal = (
        Decimal("0.15")
    )

    #
    # LEGACY FIELD.
    #
    # Оставляем для snapshot
    # совместимости.
    #
    # В новую формулу hard TP
    # это значение НЕ добавляется,
    # потому что trailing + limit
    # учитываются через
    # activation_price.
    #
    take_profit_buffer_percent: (
        Decimal
    ) = Decimal("0.30")

    fallback_buy_commission_percent: (
        Decimal
    ) = Decimal("0.30")

    fallback_sell_commission_percent: (
        Decimal
    ) = Decimal("0.30")

    min_open_positions_for_compensation: (
        int
    ) = 5

    compensation_multiplier: Decimal = (
        Decimal("3")
    )

    early_close_min_working_time_seconds: (
        int
    ) = 86400

    early_close_profit_loss_ratio: (
        Decimal
    ) = Decimal("3")

    quantity: int | Decimal = 1
    take_profit_percent: Decimal | None = None
    max_take_profit_percent: Decimal | None = None
    base_order_amount: Decimal | None = None
    order_amount_multiplier: Decimal = Decimal("1.05")
    max_order_amount_multiplier: Decimal = Decimal("3")
    quantity_step: Decimal = Decimal("1")
    min_quantity: Decimal = Decimal("0")
    min_order_amount: Decimal = Decimal("0")

    def buy_quantity(self, price: Decimal, open_positions_count: int) -> int | Decimal:
        if self.base_order_amount is None:
            return self.quantity
        positive = (
            price, self.base_order_amount, self.quantity_step,
            self.order_amount_multiplier, self.max_order_amount_multiplier,
        )
        if any(not value.is_finite() or value <= 0 for value in positive):
            raise ValueError("Order sizing values must be finite and positive")
        if self.order_amount_multiplier < 1 or self.max_order_amount_multiplier < 1:
            raise ValueError("Order amount multipliers must be at least one")
        if open_positions_count < 0:
            raise ValueError("Open positions count cannot be negative")
        if any(not value.is_finite() or value < 0 for value in (self.min_quantity, self.min_order_amount)):
            raise ValueError("Exchange minimums must be finite and nonnegative")
        amount = self.base_order_amount
        cap = amount * self.max_order_amount_multiplier
        if self.order_amount_multiplier > 1:
            for _ in range(open_positions_count):
                amount = min(amount * self.order_amount_multiplier, cap)
                if amount == cap:
                    break
        quantity = (amount / price / self.quantity_step).to_integral_value(rounding=ROUND_FLOOR) * self.quantity_step
        if quantity < self.min_quantity or quantity * price < self.min_order_amount:
            return Decimal("0")
        return quantity


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

    #
    # Цена инструмента
    # при запуске сессии.
    #
    session_start_price: (
        Decimal | None
    ) = None

    #
    # Фиксированный денежный
    # шаг сетки.
    #
    grid_step: (
        Decimal | None
    ) = None

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

    grid_opened_at: (
        datetime | None
    ) = None

    cycle_closed_orders: int = 0
    cycle_realized_profit: Decimal = Decimal("0")
    completed_cycles: list[dict] = field(default_factory=list)

    total_buy_commission: Decimal = (
        Decimal("0")
    )

    total_sell_commission: Decimal = (
        Decimal("0")
    )

    def __post_init__(
        self,
    ) -> None:
        self.levels.sort(
            key=lambda level: (
                level.index
            )
        )

        self._initialize_grid_geometry()

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

                        early_close_min_working_time_seconds=(
                            self
                            .config
                            .early_close_min_working_time_seconds
                        ),

                        early_close_profit_loss_ratio=(
                            self
                            .config
                            .early_close_profit_loss_ratio
                        ),
                    )
                ),
            )
        )

    def _initialize_grid_geometry(
        self,
    ) -> None:
        if not self.levels:
            raise ValueError(
                "Grid must contain "
                "at least one level"
            )

        if self.grid_step is None:
            if len(self.levels) >= 2:
                self.grid_step = abs(
                    self.levels[0].price
                    - self.levels[1].price
                )

            else:
                self.grid_step = (
                    self.levels[0].price
                    * Decimal("0.30")
                    / Decimal("100")
                )

        if (
            self.grid_step
            <= Decimal("0")
        ):
            raise ValueError(
                "grid_step must be positive"
            )

        if (
            self.session_start_price
            is None
        ):
            self.session_start_price = (
                self.levels[0].price
                + self.grid_step
            )

        if (
            self.session_start_price
            <= Decimal("0")
        ):
            raise ValueError(
                "session_start_price "
                "must be positive"
            )

    def on_price(
        self,
        current_price: Decimal,

        buy_reference_price: (
            Decimal | None
        ) = None,

        sell_reference_price: (
            Decimal | None
        ) = None,
    ) -> list[
        TradingCommand
    ]:
        """
        current_price — mid
        стакана (переоценка,
        риск-проверки).

        buy_reference_price —
        лучший ask: входы BUY
        смотрим сторону
        продаж.

        sell_reference_price —
        лучший bid: выходы
        SELL смотрим сторону
        покупок.

        None → текущая цена
        (обратная
        совместимость).
        """

        buy_price = (
            buy_reference_price

            if (
                buy_reference_price
                is not None
            )

            else current_price
        )

        sell_price = (
            sell_reference_price

            if (
                sell_reference_price
                is not None
            )

            else current_price
        )

        commands: list[
            TradingCommand
        ] = []

        if buy_price > 0:
            commands.extend(self._process_entries(current_price=buy_price))
        if sell_price > 0:
            commands.extend(self._process_exits(current_price=sell_price))

        if sell_price <= 0:
            return commands

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
                    sell_price
                ),
            )
        )

        commands.extend(
            self.risk_manager
            .check_early_close(
                open_positions=(
                    self.open_positions
                ),

                realized_profit=(
                    self.realized_profit
                ),

                current_price=(
                    sell_price
                ),

                grid_age_seconds=(
                    self
                    ._grid_age_seconds()
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
            self._get_level_by_index(
                event.level_index
            )
        )

        if level is None:
            return []

        if event.side == "BUY":
            self._handle_buy_execution(
                level=level,
                event=event,
            )

        elif event.side == "SELL":
            self._handle_sell_execution(
                level=level,
                event=event,
            )

        self.recalculate_planned_levels()
        return []

    def recalculate_planned_levels(self) -> None:
        if self.grid_step is None or self.session_start_price is None:
            return
        anchor = self.session_start_price
        for level in sorted(self.levels, key=lambda item: item.index):
            position = self.open_positions.get(level.index)
            if position is not None:
                anchor = position.entry_price
                if level.status != GridLevelStatus.ORDER_PLACED:
                    gross = position.purchase_cost - position.buy_commission if position.purchase_cost is not None else position.entry_price * position.quantity
                    units = self._calculate_effective_units(gross, position.entry_price)
                    cost = position.purchase_cost if position.purchase_cost is not None else gross + position.buy_commission
                    position.hard_take_profit_price = self._calculate_hard_take_profit_price(cost, units)
                continue
            if level.status == GridLevelStatus.ORDER_PLACED or level.trailing_entry is not None:
                anchor = level.price
                continue
            activation = anchor - self.grid_step
            if activation > 0:
                level.price = activation
            anchor = level.price

    def _handle_buy_execution(
        self,
        level: GridLevel,
        event: TradeExecutedEvent,
    ) -> None:
        #
        # Первый вход означает,
        # что сетка в рынке.
        #
        if not self.open_positions:
            self.grid_opened_at = (
                datetime.now(
                    timezone.utc
                )
            )

        #
        # Фактическая сумма покупки
        # БЕЗ комиссии.
        #
        gross_buy_amount = (
            self._get_gross_amount(
                price=event.price,

                quantity=(
                    event.quantity
                ),

                broker_total=(
                    event.total_amount
                ),
            )
        )

        buy_commission = (
            self._calculate_buy_commission(
                gross_amount=(
                    gross_buy_amount
                ),

                actual_commission=(
                    event.commission
                ),
            )
        )

        purchase_cost = (
            gross_buy_amount
            + buy_commission
        )

        #
        # В live цена инструмента
        # обычно указана за одну бумагу,
        # а total_amount уже содержит
        # количество бумаг в лоте.
        #
        # Поэтому выводим фактическое
        # количество ценовых единиц
        # непосредственно из суммы
        # брокера.
        #
        effective_units = (
            self._calculate_effective_units(
                gross_amount=(
                    gross_buy_amount
                ),

                execution_price=(
                    event.price
                ),
            )
        )

        hard_take_profit_price = (
            self
            ._calculate_hard_take_profit_price(
                purchase_cost=(
                    purchase_cost
                ),

                effective_units=(
                    effective_units
                ),
            )
        )

        self.total_buy_commission += (
            buy_commission
        )

        existing = self.open_positions.get(event.level_index)
        if existing is not None:
            previous_gross = (existing.purchase_cost - existing.buy_commission) if existing.purchase_cost is not None else existing.entry_price * existing.quantity
            combined_quantity = existing.quantity + event.quantity
            average_price = (existing.entry_price * existing.quantity + event.price * event.quantity) / combined_quantity
            combined_cost = (existing.purchase_cost if existing.purchase_cost is not None else previous_gross + existing.buy_commission) + purchase_cost
            self.open_positions[event.level_index] = replace(existing,
                quantity=combined_quantity, entry_price=average_price,
                buy_commission=existing.buy_commission + buy_commission, purchase_cost=combined_cost,
                hard_take_profit_price=self._calculate_hard_take_profit_price(
                    combined_cost, self._calculate_effective_units(previous_gross + gross_buy_amount, average_price),
                ),
            )
            level.price = average_price
            level.status = GridLevelStatus.POSITION_OPENED
            level.trailing_entry = None
            return
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

        #
        # Уровень запоминает
        # реальную цену исполнения.
        #
        level.price = (
            event.price
        )

        level.status = (
            GridLevelStatus
            .POSITION_OPENED
        )

        level.trailing_entry = None

    def _handle_sell_execution(
        self,
        level: GridLevel,
        event: TradeExecutedEvent,
    ) -> None:
        position = (
            self.open_positions
            .pop(
                event.level_index,
                None,
            )
        )

        partial = False
        if position is not None:
            if event.quantity < position.quantity:
                partial = True
                ratio = Decimal(event.quantity) / Decimal(position.quantity)
                closed_cost = (position.purchase_cost if position.purchase_cost is not None else position.entry_price * position.quantity + position.buy_commission) * ratio
                closed_commission = position.buy_commission * ratio
                remainder = replace(position,
                    quantity=position.quantity - event.quantity,
                    buy_commission=position.buy_commission - closed_commission,
                    purchase_cost=(position.purchase_cost - closed_cost) if position.purchase_cost is not None else None,
                )
                self.open_positions[event.level_index] = remainder
                position = replace(position, quantity=event.quantity, buy_commission=closed_commission, purchase_cost=closed_cost)
            gross_sell_amount = (
                self._get_gross_amount(
                    price=event.price,

                    quantity=(
                        event.quantity
                    ),

                    broker_total=(
                        event.total_amount
                    ),
                )
            )

            sell_commission = (
                self
                ._calculate_sell_commission(
                    gross_amount=(
                        gross_sell_amount
                    ),

                    actual_commission=(
                        event.commission
                    ),
                )
            )

            self.total_sell_commission += (
                sell_commission
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
                    position.purchase_cost
                )

            else:
                gross_buy = (
                    position.entry_price
                    * Decimal(
                        position.quantity
                    )
                )

                purchase_cost = (
                    gross_buy
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
            if not partial:
                self.cycle_closed_orders += 1
            self.cycle_realized_profit += profit

        if not self.open_positions and position is not None:
            self.completed_cycles.append({
                "started_at": self.grid_opened_at.isoformat() if self.grid_opened_at else None,
                "closed_at": datetime.now(timezone.utc).isoformat(),
                "closed_orders": self.cycle_closed_orders,
                "profit": str(self.cycle_realized_profit),
            })
        if not self.open_positions:
            self.cycle_closed_orders = 0
            self.cycle_realized_profit = Decimal("0")
            self.grid_opened_at = (
                None
            )

        #
        # Уровень снова разрешён.
        #
        level.status = GridLevelStatus.POSITION_OPENED if partial else GridLevelStatus.WAITING_PRICE

        level.trailing_entry = None

    def recover_position(
        self,
        quantity: int | Decimal,
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
                not in self.open_positions
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

        #
        # Legacy recovery не знает
        # broker total_amount.
        #
        gross_buy_amount = (
            entry_price
            * Decimal(quantity)
        )

        buy_commission = (
            self._calculate_buy_commission(
                gross_amount=(
                    gross_buy_amount
                ),

                actual_commission=None,
            )
        )

        purchase_cost = (
            gross_buy_amount
            + buy_commission
        )

        hard_take_profit_price = (
            self
            ._calculate_hard_take_profit_price(
                purchase_cost=(
                    purchase_cost
                ),

                effective_units=(
                    Decimal(quantity)
                ),
            )
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

        level.price = (
            entry_price
        )

        level.status = (
            GridLevelStatus
            .POSITION_OPENED
        )

        level.trailing_entry = None

        if (
            self.grid_opened_at
            is None
        ):
            self.grid_opened_at = (
                datetime.now(
                    timezone.utc
                )
            )

    def _grid_age_seconds(
        self,
    ) -> int | None:
        if (
            self.grid_opened_at
            is None
        ):
            return None

        now = (
            datetime.now(
                timezone.utc
            )
        )

        age = (
            now
            - self.grid_opened_at
        )

        return int(
            age.total_seconds()
        )

    # ========================================================
    # BUY
    # ========================================================

    def _process_entries(
        self,
        current_price: Decimal,
    ) -> list[
        TradingCommand
    ]:
        active_entry_level = (
            self._find_active_entry_level()
        )

        if active_entry_level is None:
            level = (
                self._find_next_entry_level(
                    current_price=(
                        current_price
                    )
                )
            )

            if level is not None:
                self._activate_entry_trailing(
                    level=level,

                    current_price=(
                        current_price
                    ),
                )

                active_entry_level = (
                    level
                )

        if active_entry_level is None:
            return []

        if (
            active_entry_level
            .trailing_entry
            is None
        ):
            return []

        if (
            active_entry_level.status
            == GridLevelStatus
            .ORDER_PLACED
        ):
            return []

        active_entry_level.trailing_entry = (
            self.trailing_engine
            .update_entry(
                state=(
                    active_entry_level
                    .trailing_entry
                ),

                current_price=(
                    current_price
                ),
            )
        )

        if not (
            active_entry_level
            .trailing_entry
            .is_confirmed
        ):
            return []

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

        quantity = self.config.buy_quantity(buy_price, len(self.open_positions))
        if quantity <= 0:
            return []

        active_entry_level.status = (
            GridLevelStatus
            .ORDER_PLACED
        )

        return [
            PlaceBuyLimitCommand(
                instrument_id=(
                    self.instrument_id
                ),

                level_index=(
                    active_entry_level.index
                ),

                quantity=quantity,
                commission_percent=self.config.fallback_buy_commission_percent,

                price=(
                    buy_price
                ),
            )
        ]

    def _find_active_entry_level(
        self,
    ) -> GridLevel | None:
        for level in self.levels:
            if (
                level.status
                == GridLevelStatus
                .TRAILING_ENTRY
            ):
                return level

            if (
                level.status
                == GridLevelStatus
                .ORDER_PLACED
                and level.trailing_entry
                is not None
            ):
                return level

        return None

    def _find_next_entry_level(
        self,
        current_price: Decimal,
    ) -> GridLevel | None:
        #
        # Первый уровень.
        #
        if not self.open_positions:
            first_level = (
                self._get_level_by_index(
                    1
                )
            )

            if first_level is None:
                return None

            if (
                first_level.status
                != GridLevelStatus
                .WAITING_PRICE
            ):
                return None

            if (
                self
                ._first_entry_activation_reached(
                    current_price=(
                        current_price
                    )
                )
            ):
                return first_level

            return None

        #
        # Уровни №2...N.
        #
        # Каждый строится от
        # реальной покупки
        # предыдущего уровня.
        #
        for level in self.levels:
            if level.index <= 1:
                continue

            if (
                level.status
                != GridLevelStatus
                .WAITING_PRICE
            ):
                continue

            if (
                level.index
                in self.open_positions
            ):
                continue

            previous_position = (
                self.open_positions
                .get(
                    level.index - 1
                )
            )

            if (
                previous_position
                is None
            ):
                continue

            grid_step = self.grid_step
            if grid_step is None:
                raise ValueError("grid_step must be initialized")
            activation_price = (
                previous_position
                .entry_price
                - grid_step
            )

            level.price = (
                activation_price
            )

            if (
                current_price
                <= activation_price
            ):
                return level

        return None

    def _activate_entry_trailing(
        self,
        level: GridLevel,
        current_price: Decimal,
    ) -> None:
        level.status = (
            GridLevelStatus
            .TRAILING_ENTRY
        )

        level.trailing_entry = (
            self.trailing_engine
            .create_entry(
                activation_price=(
                    current_price
                )
            )
        )

    def _first_entry_activation_reached(
        self,
        current_price: Decimal,
    ) -> bool:
        if (
            self.session_start_price
            is None
        ):
            return False

        deviation = abs(
            current_price
            - self.session_start_price
        )

        deviation_percent = (
            deviation
            / self.session_start_price
            * Decimal("100")
        )

        return (
            deviation_percent
            >= self.config
            .first_entry_activation_percent
        )

    # ========================================================
    # SELL
    # ========================================================

    def _process_exits(
        self,
        current_price: Decimal,
    ) -> list[
        TradingCommand
    ]:
        commands: list[
            TradingCommand
        ] = []

        #
        # Каждую позицию считаем
        # независимо.
        #
        for (
            level_index,
            position,
        ) in list(
            self.open_positions
            .items()
        ):
            level = (
                self._get_level_by_index(
                    level_index
                )
            )

            if level is None:
                continue

            #
            # Pending SELL.
            #
            # trailing_entry == None
            # отличает его от BUY order.
            #
            if (
                level.status
                == GridLevelStatus
                .ORDER_PLACED
                and level.trailing_entry
                is None
            ):
                continue

            if position.purchase_cost is not None and position.entry_price > 0:
                units = self._calculate_effective_units(
                    position.purchase_cost - position.buy_commission, position.entry_price,
                )
                position.hard_take_profit_price = max(
                    position.hard_take_profit_price,
                    self._calculate_hard_take_profit_price(position.purchase_cost, units),
                )

            activation_price = (
                self
                ._calculate_exit_activation_price(
                    hard_take_profit_price=(
                        position
                        .hard_take_profit_price
                    )
                )
            )

            #
            # Цена ещё не дошла до
            # безопасной точки запуска
            # trailing.
            #
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
                        #
                        # target_price —
                        # именно минимальная
                        # прибыльная SELL price.
                        #
                        target_price=(
                            position
                            .hard_take_profit_price
                        ),

                        highest_price=(
                            current_price
                        ),
                    )
                )

            #
            # Каждый новый максимум
            # поднимает SELL trailing.
            #
            position.trailing_exit = (
                self.trailing_engine
                .update_exit(
                    state=(
                        position
                        .trailing_exit
                    ),

                current_price=(
                    current_price
                ),
            )
        )

            max_take_profit_reached = (
                self.config.max_take_profit_percent is not None
                and current_price >= position.entry_price * (
                    Decimal("1") + self.config.max_take_profit_percent / Decimal("100")
                )
            )
            if not position.trailing_exit.is_confirmed and not max_take_profit_reached:
                continue

            #
            # Trailing задет.
            #
            # Лимитку ставим ещё
            # на 0.15% ниже рынка.
            #
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

            #
            # Абсолютная страховка:
            # никогда не выставляем
            # SELL ниже цены,
            # гарантирующей min profit.
            #
            if (
                sell_price
                < position
                .hard_take_profit_price
            ):
                sell_price = (
                    position
                    .hard_take_profit_price
                )

            commands.append(
                PlaceSellLimitCommand(
                    instrument_id=(
                        self.instrument_id
                    ),

                    level_index=(
                        position.level_index
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

    def _calculate_hard_take_profit_price(
        self,
        purchase_cost: Decimal,
        effective_units: Decimal,
    ) -> Decimal:
        """
        Минимальная цена SELL,
        которая после ожидаемой
        комиссии продажи обеспечивает
        min_profit_percent ЧИСТЫМИ
        относительно purchase_cost.

        purchase_cost уже содержит
        фактическую BUY-комиссию.
        """

        if (
            purchase_cost
            <= Decimal("0")
        ):
            raise ValueError(
                "purchase_cost "
                "must be positive"
            )

        if (
            effective_units
            <= Decimal("0")
        ):
            raise ValueError(
                "effective_units "
                "must be positive"
            )

        min_profit_rate = (
            self.config
            .min_profit_percent
            / Decimal("100")
        )

        expected_sell_commission_rate = (
            self.config
            .fallback_sell_commission_percent
            / Decimal("100")
        )

        if (
            expected_sell_commission_rate
            >= Decimal("1")
        ):
            raise ValueError(
                "Invalid sell commission"
            )

        #
        # Сколько денег должно
        # остаться ПОСЛЕ SELL commission.
        #
        required_net_sell_amount = (
            purchase_cost
            * (
                Decimal("1")
                + min_profit_rate
            )
        )

        #
        # Сколько нужно получить
        # ДО SELL commission.
        #
        required_gross_sell_amount = (
            required_net_sell_amount
            / (
                Decimal("1")
                - expected_sell_commission_rate
            )
        )

        return (
            required_gross_sell_amount
            / effective_units
        )

    def _calculate_exit_activation_price(
        self,
        hard_take_profit_price: Decimal,
    ) -> Decimal:
        """
        Цена, с которой можно
        безопасно запустить SELL trailing.

        После:
          -0.15% trailing
          -0.15% limit

        выставляемая лимитка должна
        оставаться >= hard TP.
        """

        trailing_multiplier = (
            Decimal("1")
            - (
                self.config
                .trailing_percent
                / Decimal("100")
            )
        )

        sell_limit_multiplier = (
            Decimal("1")
            - (
                self.config
                .exit_limit_offset_percent
                / Decimal("100")
            )
        )

        combined_multiplier = (
            trailing_multiplier
            * sell_limit_multiplier
        )

        if (
            combined_multiplier
            <= Decimal("0")
        ):
            raise ValueError(
                "Invalid trailing/exit "
                "configuration"
            )

        activation = hard_take_profit_price / combined_multiplier
        if self.config.take_profit_percent is not None:
            activation = max(activation, hard_take_profit_price / (
                Decimal("1") + self.config.min_profit_percent / Decimal("100")
            ) * (Decimal("1") + self.config.take_profit_percent / Decimal("100")))
        return activation

    # ========================================================
    # MONEY
    # ========================================================

    def _get_gross_amount(
        self,
        price: Decimal,
        quantity: int | Decimal,
        broker_total: (
            Decimal | None
        ),
    ) -> Decimal:
        #
        # LIVE:
        # источник истины —
        # фактическая сумма брокера.
        #
        if (
            broker_total
            is not None
            and broker_total
            > Decimal("0")
        ):
            return broker_total

        #
        # Sandbox / legacy.
        #
        return (
            price
            * Decimal(quantity)
        )

    def _calculate_effective_units(
        self,
        gross_amount: Decimal,
        execution_price: Decimal,
    ) -> Decimal:
        if (
            execution_price
            <= Decimal("0")
        ):
            raise ValueError(
                "execution_price "
                "must be positive"
            )

        return (
            gross_amount
            / execution_price
        )

    def _calculate_buy_commission(
        self,
        gross_amount: Decimal,
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
            gross_amount
            * self.config
            .fallback_buy_commission_percent
            / Decimal("100")
        )

    def _calculate_sell_commission(
        self,
        gross_amount: Decimal,
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
            gross_amount
            * self.config
            .fallback_sell_commission_percent
            / Decimal("100")
        )

    def _get_level_by_index(
        self,
        level_index: int,
    ) -> GridLevel | None:
        for level in self.levels:
            if (
                level.index
                == level_index
            ):
                return level

        return None
