from __future__ import annotations

from dataclasses import (
    dataclass,
    field,
)
from decimal import Decimal
from typing import Any


def _decimal_to_str(
    value: Decimal | None,
) -> str | None:
    if value is None:
        return None

    return str(value)


def _str_to_decimal(
    value: str | None,
) -> Decimal | None:
    if value is None:
        return None

    return Decimal(value)


def _quantity_from_value(value: Any) -> int | Decimal:
    quantity = Decimal(str(value))
    return int(quantity) if quantity == quantity.to_integral_value() else quantity


def _quantity_to_value(value: int | Decimal) -> int | str:
    return str(value) if isinstance(value, Decimal) else value


@dataclass(slots=True)
class GridEngineConfigState:
    entry_limit_offset_percent: Decimal
    exit_limit_offset_percent: Decimal

    entry_rebound_percent: Decimal
    trailing_percent: Decimal

    min_profit_percent: Decimal

    take_profit_buffer_percent: Decimal

    fallback_buy_commission_percent: (
        Decimal
    )

    fallback_sell_commission_percent: (
        Decimal
    )

    min_open_positions_for_compensation: (
        int
    )

    compensation_multiplier: Decimal

    quantity: int | Decimal
    take_profit_percent: Decimal | None = None
    max_take_profit_percent: Decimal | None = None
    base_order_amount: Decimal | None = None
    order_amount_multiplier: Decimal = Decimal("1.05")
    max_order_amount_multiplier: Decimal = Decimal("3")
    quantity_step: Decimal = Decimal("1")
    min_quantity: Decimal = Decimal("0")
    min_order_amount: Decimal = Decimal("0")

    early_close_min_working_time_seconds: (
        int
    ) = 86400

    early_close_profit_loss_ratio: (
        Decimal
    ) = Decimal("3")


@dataclass(slots=True)
class GridLevelState:
    level_index: int
    level_price: Decimal

    status: str

    trailing_entry_lowest_price: (
        Decimal | None
    ) = None

    trailing_entry_confirmed: (
        bool
    ) = False


@dataclass(slots=True)
class OpenPositionState:
    level_index: int

    entry_price: Decimal

    #
    # Количество лотов.
    #
    quantity: int | Decimal

    buy_commission: Decimal

    hard_take_profit_price: Decimal

    expected_sell_commission_percent: (
        Decimal
    )

    trailing_exit_target_price: (
        Decimal | None
    ) = None

    trailing_exit_highest_price: (
        Decimal | None
    ) = None

    trailing_exit_confirmed: (
        bool
    ) = False

    #
    # Полная фактическая стоимость
    # покупки с BUY-комиссией.
    #
    purchase_cost: (
        Decimal | None
    ) = None


@dataclass(slots=True)
class BrokerOrderState:
    broker_order_id: str

    request_id: str | None

    instrument_uid: str
    ticker: str

    level_index: int | None

    side: str

    quantity: int | Decimal

    limit_price: Decimal

    status: str

    lots_requested: int | Decimal = 0
    lots_executed: int | Decimal = 0

    executed_price: (
        Decimal | None
    ) = None


@dataclass(slots=True)
class CapitalReservationState:
    instrument_uid: str

    level_index: int

    amount: Decimal


@dataclass(slots=True)
class InstrumentTradingState:
    ticker: str

    instrument_uid: str

    current_price: (
        Decimal | None
    )

    realized_profit: Decimal

    levels: list[
        GridLevelState
    ] = field(
        default_factory=list
    )

    open_positions: list[
        OpenPositionState
    ] = field(
        default_factory=list
    )

    active_orders: list[
        BrokerOrderState
    ] = field(
        default_factory=list
    )

    grid_config: (
        GridEngineConfigState | None
    ) = None

    #
    # Накопленные комиссии
    # конкретного инструмента.
    #
    total_buy_commission: Decimal = (
        Decimal("0")
    )

    total_sell_commission: Decimal = (
        Decimal("0")
    )

    grid_opened_at: (
        str | None
    ) = None

    cycle_closed_orders: int = 0
    cycle_realized_profit: Decimal = Decimal("0")
    completed_cycles: list[dict] = field(default_factory=list)
    cycle_price_points: list[dict] = field(default_factory=list)
    session_start_price: Decimal | None = None
    grid_step: Decimal | None = None


@dataclass(slots=True)
class TradingSessionState:
    schema_version: int

    session_id: str

    trading_account_id: str

    broker_account_id: str

    mode: str
    status: str

    available_cash: Decimal
    reserved_cash: Decimal

    instruments: list[
        InstrumentTradingState
    ] = field(
        default_factory=list
    )

    portfolio_cash: (
        Decimal | None
    ) = None

    reservations: list[
        CapitalReservationState
    ] = field(
        default_factory=list
    )

    #
    # Фиксируется при первом
    # snapshot сессии.
    #
    # После рестарта НЕ пересчитываем.
    #
    initial_deposit: (
        Decimal | None
    ) = None

    total_buy_commission: Decimal = (
        Decimal("0")
    )

    total_sell_commission: Decimal = (
        Decimal("0")
    )

    started_at: str | None = None

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "schema_version":
                self.schema_version,

            "session_id":
                self.session_id,

            "started_at": self.started_at,

            "trading_account_id":
                self
                .trading_account_id,

            "broker_account_id":
                self
                .broker_account_id,

            "mode":
                self.mode,

            "status":
                self.status,

            "available_cash":
                str(
                    self.available_cash
                ),

            "reserved_cash":
                str(
                    self.reserved_cash
                ),

            "portfolio_cash":
                _decimal_to_str(
                    self.portfolio_cash
                ),

            "initial_deposit":
                _decimal_to_str(
                    self.initial_deposit
                ),

            "total_buy_commission":
                str(
                    self
                    .total_buy_commission
                ),

            "total_sell_commission":
                str(
                    self
                    .total_sell_commission
                ),

            "reservations": [
                {
                    "instrument_uid":
                        item
                        .instrument_uid,

                    "level_index":
                        item
                        .level_index,

                    "amount":
                        str(
                            item.amount
                        ),
                }
                for item
                in self.reservations
            ],

            "instruments": [
                self
                ._instrument_to_dict(
                    instrument
                )
                for instrument
                in self.instruments
            ],
        }

    @staticmethod
    def _instrument_to_dict(
        instrument: (
            InstrumentTradingState
        ),
    ) -> dict[str, Any]:
        config = (
            instrument.grid_config
        )

        return {
            "ticker":
                instrument.ticker,

            "instrument_uid":
                instrument
                .instrument_uid,

            "current_price":
                _decimal_to_str(
                    instrument
                    .current_price
                ),

            "realized_profit":
                str(
                    instrument
                    .realized_profit
                ),

            "total_buy_commission":
                str(
                    instrument
                    .total_buy_commission
                ),

            "total_sell_commission":
                str(
                    instrument
                    .total_sell_commission
                ),

            "grid_opened_at":
                instrument
                .grid_opened_at,

            "completed_cycles": instrument.completed_cycles,
            "cycle_price_points": instrument.cycle_price_points,
            "cycle_closed_orders": instrument.cycle_closed_orders,
            "cycle_realized_profit": str(instrument.cycle_realized_profit),
            "session_start_price": _decimal_to_str(instrument.session_start_price),
            "grid_step": _decimal_to_str(instrument.grid_step),

            "grid_config": (
                {
                    "entry_limit_offset_percent":
                        str(
                            config
                            .entry_limit_offset_percent
                        ),

                    "exit_limit_offset_percent":
                        str(
                            config
                            .exit_limit_offset_percent
                        ),

                    "entry_rebound_percent":
                        str(
                            config
                            .entry_rebound_percent
                        ),

                    "trailing_percent":
                        str(
                            config
                            .trailing_percent
                        ),

                    "min_profit_percent":
                        str(
                            config
                            .min_profit_percent
                        ),

                    "take_profit_percent": _decimal_to_str(config.take_profit_percent),
                    "max_take_profit_percent": _decimal_to_str(config.max_take_profit_percent),
                    "base_order_amount": _decimal_to_str(config.base_order_amount),
                    "order_amount_multiplier": str(config.order_amount_multiplier),
                    "max_order_amount_multiplier": str(config.max_order_amount_multiplier),
                    "quantity_step": str(config.quantity_step),
                    "min_quantity": str(config.min_quantity),
                    "min_order_amount": str(config.min_order_amount),

                    "take_profit_buffer_percent":
                        str(
                            config
                            .take_profit_buffer_percent
                        ),

                    "fallback_buy_commission_percent":
                        str(
                            config
                            .fallback_buy_commission_percent
                        ),

                    "fallback_sell_commission_percent":
                        str(
                            config
                            .fallback_sell_commission_percent
                        ),

                    "min_open_positions_for_compensation":
                        config
                        .min_open_positions_for_compensation,

                    "compensation_multiplier":
                        str(
                            config
                            .compensation_multiplier
                        ),

                    "quantity":
                        _quantity_to_value(config.quantity),

                    "early_close_min_working_time_seconds":
                        config
                        .early_close_min_working_time_seconds,

                    "early_close_profit_loss_ratio":
                        str(
                            config
                            .early_close_profit_loss_ratio
                        ),
                }
                if config is not None
                else None
            ),

            "levels": [
                {
                    "level_index":
                        level
                        .level_index,

                    "level_price":
                        str(
                            level
                            .level_price
                        ),

                    "status":
                        level.status,

                    "trailing_entry_lowest_price":
                        _decimal_to_str(
                            level
                            .trailing_entry_lowest_price
                        ),

                    "trailing_entry_confirmed":
                        level
                        .trailing_entry_confirmed,
                }
                for level
                in instrument.levels
            ],

            "open_positions": [
                {
                    "level_index":
                        position
                        .level_index,

                    "entry_price":
                        str(
                            position
                            .entry_price
                        ),

                    "quantity":
                        _quantity_to_value(position.quantity),

                    "buy_commission":
                        str(
                            position
                            .buy_commission
                        ),

                    "hard_take_profit_price":
                        str(
                            position
                            .hard_take_profit_price
                        ),

                    "expected_sell_commission_percent":
                        str(
                            position
                            .expected_sell_commission_percent
                        ),

                    "trailing_exit_target_price":
                        _decimal_to_str(
                            position
                            .trailing_exit_target_price
                        ),

                    "trailing_exit_highest_price":
                        _decimal_to_str(
                            position
                            .trailing_exit_highest_price
                        ),

                    "trailing_exit_confirmed":
                        position
                        .trailing_exit_confirmed,

                    "purchase_cost":
                        _decimal_to_str(
                            position
                            .purchase_cost
                        ),
                }
                for position
                in instrument
                .open_positions
            ],

            "active_orders": [
                {
                    "broker_order_id":
                        order
                        .broker_order_id,

                    "request_id":
                        order
                        .request_id,

                    "instrument_uid":
                        order
                        .instrument_uid,

                    "ticker":
                        order.ticker,

                    "level_index":
                        order
                        .level_index,

                    "side":
                        order.side,

                    "quantity":
                        _quantity_to_value(order.quantity),

                    "limit_price":
                        str(
                            order
                            .limit_price
                        ),

                    "status":
                        order.status,

                    "lots_requested":
                        _quantity_to_value(order.lots_requested),

                    "lots_executed":
                        _quantity_to_value(order.lots_executed),

                    "executed_price":
                        _decimal_to_str(
                            order
                            .executed_price
                        ),
                }
                for order
                in instrument
                .active_orders
            ],
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> "TradingSessionState":
        instruments = [
            cls._instrument_from_dict(
                item
            )
            for item
            in data.get(
                "instruments",
                [],
            )
        ]

        reservations = [
            CapitalReservationState(
                instrument_uid=str(
                    item[
                        "instrument_uid"
                    ]
                ),

                level_index=int(
                    item[
                        "level_index"
                    ]
                ),

                amount=Decimal(
                    item[
                        "amount"
                    ]
                ),
            )
            for item
            in data.get(
                "reservations",
                [],
            )
        ]

        return cls(
            schema_version=int(
                data[
                    "schema_version"
                ]
            ),

            session_id=str(
                data[
                    "session_id"
                ]
            ),

            trading_account_id=str(
                data[
                    "trading_account_id"
                ]
            ),

            broker_account_id=str(
                data[
                    "broker_account_id"
                ]
            ),

            mode=str(
                data[
                    "mode"
                ]
            ),

            status=str(
                data[
                    "status"
                ]
            ),

            available_cash=Decimal(
                data[
                    "available_cash"
                ]
            ),

            reserved_cash=Decimal(
                data[
                    "reserved_cash"
                ]
            ),

            instruments=instruments,
            started_at=str(data["started_at"]) if data.get("started_at") else None,

            portfolio_cash=(
                _str_to_decimal(
                    data.get(
                        "portfolio_cash"
                    )
                )
            ),

            reservations=(
                reservations
            ),

            initial_deposit=(
                _str_to_decimal(
                    data.get(
                        "initial_deposit"
                    )
                )
            ),

            total_buy_commission=Decimal(
                data.get(
                    "total_buy_commission",
                    "0",
                )
            ),

            total_sell_commission=Decimal(
                data.get(
                    "total_sell_commission",
                    "0",
                )
            ),
        )

    @staticmethod
    def _instrument_from_dict(
        data: dict[str, Any],
    ) -> InstrumentTradingState:
        raw_config = data.get(
            "grid_config"
        )

        grid_config = None

        if raw_config is not None:
            grid_config = (
                GridEngineConfigState(
                    take_profit_percent=_str_to_decimal(raw_config.get("take_profit_percent")),
                    max_take_profit_percent=_str_to_decimal(raw_config.get("max_take_profit_percent")),
                    base_order_amount=_str_to_decimal(raw_config.get("base_order_amount")),
                    order_amount_multiplier=Decimal(raw_config.get("order_amount_multiplier", "1.05")),
                    max_order_amount_multiplier=Decimal(raw_config.get("max_order_amount_multiplier", "3")),
                    quantity_step=Decimal(raw_config.get("quantity_step", "1")),
                    min_quantity=Decimal(raw_config.get("min_quantity", "0")),
                    min_order_amount=Decimal(raw_config.get("min_order_amount", "0")),
                    entry_limit_offset_percent=Decimal(
                        raw_config[
                            "entry_limit_offset_percent"
                        ]
                    ),

                    exit_limit_offset_percent=Decimal(
                        raw_config[
                            "exit_limit_offset_percent"
                        ]
                    ),

                    entry_rebound_percent=Decimal(
                        raw_config[
                            "entry_rebound_percent"
                        ]
                    ),

                    trailing_percent=Decimal(
                        raw_config[
                            "trailing_percent"
                        ]
                    ),

                    min_profit_percent=Decimal(
                        raw_config[
                            "min_profit_percent"
                        ]
                    ),

                    take_profit_buffer_percent=Decimal(
                        raw_config[
                            "take_profit_buffer_percent"
                        ]
                    ),

                    fallback_buy_commission_percent=Decimal(
                        raw_config[
                            "fallback_buy_commission_percent"
                        ]
                    ),

                    fallback_sell_commission_percent=Decimal(
                        raw_config[
                            "fallback_sell_commission_percent"
                        ]
                    ),

                    min_open_positions_for_compensation=int(
                        raw_config[
                            "min_open_positions_for_compensation"
                        ]
                    ),

                    compensation_multiplier=Decimal(
                        raw_config[
                            "compensation_multiplier"
                        ]
                    ),

                    quantity=_quantity_from_value(
                        raw_config[
                            "quantity"
                        ]
                    ),

                    early_close_min_working_time_seconds=int(
                        raw_config.get(
                            "early_close_min_working_time_seconds",

                            86400,
                        )
                    ),

                    early_close_profit_loss_ratio=Decimal(
                        raw_config.get(
                            "early_close_profit_loss_ratio",

                            "3",
                        )
                    ),
                )
            )

        levels = [
            GridLevelState(
                level_index=int(
                    level[
                        "level_index"
                    ]
                ),

                level_price=Decimal(
                    level[
                        "level_price"
                    ]
                ),

                status=str(
                    level[
                        "status"
                    ]
                ),

                trailing_entry_lowest_price=(
                    _str_to_decimal(
                        level.get(
                            "trailing_entry_lowest_price"
                        )
                    )
                ),

                trailing_entry_confirmed=bool(
                    level.get(
                        "trailing_entry_confirmed",
                        False,
                    )
                ),
            )
            for level
            in data.get(
                "levels",
                [],
            )
        ]

        positions = [
            OpenPositionState(
                level_index=int(
                    position[
                        "level_index"
                    ]
                ),

                entry_price=Decimal(
                    position[
                        "entry_price"
                    ]
                ),

                quantity=_quantity_from_value(
                    position[
                        "quantity"
                    ]
                ),

                buy_commission=Decimal(
                    position[
                        "buy_commission"
                    ]
                ),

                hard_take_profit_price=Decimal(
                    position[
                        "hard_take_profit_price"
                    ]
                ),

                expected_sell_commission_percent=Decimal(
                    position[
                        "expected_sell_commission_percent"
                    ]
                ),

                trailing_exit_target_price=(
                    _str_to_decimal(
                        position.get(
                            "trailing_exit_target_price"
                        )
                    )
                ),

                trailing_exit_highest_price=(
                    _str_to_decimal(
                        position.get(
                            "trailing_exit_highest_price"
                        )
                    )
                ),

                trailing_exit_confirmed=bool(
                    position.get(
                        "trailing_exit_confirmed",
                        False,
                    )
                ),

                purchase_cost=(
                    _str_to_decimal(
                        position.get(
                            "purchase_cost"
                        )
                    )
                ),
            )
            for position
            in data.get(
                "open_positions",
                [],
            )
        ]

        orders = [
            BrokerOrderState(
                broker_order_id=str(
                    order[
                        "broker_order_id"
                    ]
                ),

                request_id=(
                    order.get(
                        "request_id"
                    )
                ),

                instrument_uid=str(
                    order[
                        "instrument_uid"
                    ]
                ),

                ticker=str(
                    order[
                        "ticker"
                    ]
                ),

                level_index=(
                    int(
                        order[
                            "level_index"
                        ]
                    )
                    if (
                        order.get(
                            "level_index"
                        )
                        is not None
                    )
                    else None
                ),

                side=str(
                    order[
                        "side"
                    ]
                ),

                quantity=_quantity_from_value(
                    order[
                        "quantity"
                    ]
                ),

                limit_price=Decimal(
                    order[
                        "limit_price"
                    ]
                ),

                status=str(
                    order[
                        "status"
                    ]
                ),

                lots_requested=_quantity_from_value(
                    order.get(
                        "lots_requested",
                        0,
                    )
                ),

                lots_executed=_quantity_from_value(
                    order.get(
                        "lots_executed",
                        0,
                    )
                ),

                executed_price=(
                    _str_to_decimal(
                        order.get(
                            "executed_price"
                        )
                    )
                ),
            )
            for order
            in data.get(
                "active_orders",
                [],
            )
        ]

        return InstrumentTradingState(
            ticker=str(
                data[
                    "ticker"
                ]
            ),

            instrument_uid=str(
                data[
                    "instrument_uid"
                ]
            ),

            current_price=(
                _str_to_decimal(
                    data.get(
                        "current_price"
                    )
                )
            ),

            realized_profit=Decimal(
                data.get(
                    "realized_profit",
                    "0",
                )
            ),

            levels=levels,

            open_positions=positions,

            active_orders=orders,

            grid_config=grid_config,

            total_buy_commission=Decimal(
                data.get(
                    "total_buy_commission",
                    "0",
                )
            ),

            total_sell_commission=Decimal(
                data.get(
                    "total_sell_commission",
                    "0",
                )
            ),

            grid_opened_at=(
                data.get(
                    "grid_opened_at"
                )
            ),
            completed_cycles=list(data.get("completed_cycles", [])),
            cycle_price_points=list(data.get("cycle_price_points", [])),
            cycle_closed_orders=int(data.get("cycle_closed_orders", 0)),
            cycle_realized_profit=Decimal(data.get("cycle_realized_profit", "0")),
            session_start_price=_str_to_decimal(data.get("session_start_price")),
            grid_step=_str_to_decimal(data.get("grid_step")),
        )
