from __future__ import annotations

from dataclasses import dataclass, field
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


@dataclass(slots=True)
class GridEngineConfigState:
    entry_limit_offset_percent: Decimal
    exit_limit_offset_percent: Decimal

    entry_rebound_percent: Decimal
    trailing_percent: Decimal

    min_profit_percent: Decimal
    take_profit_buffer_percent: Decimal

    fallback_buy_commission_percent: Decimal
    fallback_sell_commission_percent: Decimal

    min_open_positions_for_compensation: int
    compensation_multiplier: Decimal

    quantity: int


@dataclass(slots=True)
class GridLevelState:
    level_index: int
    level_price: Decimal
    status: str

    trailing_entry_lowest_price: (
        Decimal | None
    ) = None

    trailing_entry_confirmed: bool = False


@dataclass(slots=True)
class OpenPositionState:
    level_index: int

    entry_price: Decimal
    quantity: int

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

    trailing_exit_confirmed: bool = False


@dataclass(slots=True)
class BrokerOrderState:
    broker_order_id: str
    request_id: str | None

    instrument_uid: str
    ticker: str

    level_index: int | None

    side: str

    quantity: int
    limit_price: Decimal

    status: str

    lots_requested: int = 0
    lots_executed: int = 0

    executed_price: Decimal | None = None


@dataclass(slots=True)
class CapitalReservationState:
    instrument_uid: str
    level_index: int
    amount: Decimal


@dataclass(slots=True)
class InstrumentTradingState:
    ticker: str
    instrument_uid: str

    current_price: Decimal | None
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

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "schema_version":
                self.schema_version,

            "session_id":
                self.session_id,

            "trading_account_id":
                self.trading_account_id,

            "broker_account_id":
                self.broker_account_id,

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

            "reservations": [
                {
                    "instrument_uid":
                        item.instrument_uid,

                    "level_index":
                        item.level_index,

                    "amount":
                        str(
                            item.amount
                        ),
                }
                for item
                in self.reservations
            ],

            "instruments": [
                self._instrument_to_dict(
                    instrument
                )
                for instrument
                in self.instruments
            ],
        }

    @staticmethod
    def _instrument_to_dict(
        instrument: InstrumentTradingState,
    ) -> dict[str, Any]:
        config = (
            instrument.grid_config
        )

        return {
            "ticker":
                instrument.ticker,

            "instrument_uid":
                instrument.instrument_uid,

            "current_price":
                _decimal_to_str(
                    instrument.current_price
                ),

            "realized_profit":
                str(
                    instrument.realized_profit
                ),

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
                        config.quantity,
                }
                if config is not None
                else None
            ),

            "levels": [
                {
                    "level_index":
                        level.level_index,

                    "level_price":
                        str(
                            level.level_price
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
                        position.level_index,

                    "entry_price":
                        str(
                            position.entry_price
                        ),

                    "quantity":
                        position.quantity,

                    "buy_commission":
                        str(
                            position.buy_commission
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
                }
                for position
                in instrument.open_positions
            ],

            "active_orders": [
                {
                    "broker_order_id":
                        order.broker_order_id,

                    "request_id":
                        order.request_id,

                    "instrument_uid":
                        order.instrument_uid,

                    "ticker":
                        order.ticker,

                    "level_index":
                        order.level_index,

                    "side":
                        order.side,

                    "quantity":
                        order.quantity,

                    "limit_price":
                        str(
                            order.limit_price
                        ),

                    "status":
                        order.status,

                    "lots_requested":
                        order.lots_requested,

                    "lots_executed":
                        order.lots_executed,

                    "executed_price":
                        _decimal_to_str(
                            order.executed_price
                        ),
                }
                for order
                in instrument.active_orders
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

            portfolio_cash=(
                _str_to_decimal(
                    data.get(
                        "portfolio_cash"
                    )
                )
            ),

            reservations=reservations,
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

                    quantity=int(
                        raw_config[
                            "quantity"
                        ]
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

                quantity=int(
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

                quantity=int(
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

                lots_requested=int(
                    order.get(
                        "lots_requested",
                        0,
                    )
                ),

                lots_executed=int(
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
        )
