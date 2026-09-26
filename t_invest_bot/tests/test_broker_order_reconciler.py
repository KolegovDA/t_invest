from decimal import Decimal

from broker.broker_order_reconciler import (
    BrokerOrderReconciler,
)
from broker.live_order_manager import (
    LiveOrderManager,
    LiveOrderRecord,
)
from domain.commands import (
    PlaceBuyLimitCommand,
    PlaceSellLimitCommand,
)
from domain.enums import (
    GridLevelStatus,
)
from domain.order_execution import (
    BrokerActiveOrder,
    PlacedOrder,
)
from domain.positions import (
    OpenLevelPosition,
)
from strategy.grid_engine import (
    GridEngine,
    GridEngineConfig,
    GridLevel,
)
from strategy.trailing_engine import (
    TrailingEntryState,
)


class FakeOrderExecutor:
    def place_limit_buy(
        self,
        account_id: str,
        instrument_id: str,
        quantity: int,
        price: Decimal,
    ) -> PlacedOrder:
        return PlacedOrder(
            order_id="order-1",
        )

    def place_limit_sell(
        self,
        account_id: str,
        instrument_id: str,
        quantity: int,
        price: Decimal,
    ) -> PlacedOrder:
        return PlacedOrder(
            order_id="order-1",
        )

    def cancel_order(
        self,
        account_id: str,
        order_id: str,
    ) -> None:
        pass


def create_engine(
    with_position: bool = False,
) -> GridEngine:
    engine = GridEngine(
        instrument_id="SBER",

        levels=[
            GridLevel(
                index=1,
                price=Decimal(
                    "299"
                ),
            ),

            GridLevel(
                index=2,
                price=Decimal(
                    "298"
                ),
            ),
        ],

        config=(
            GridEngineConfig(
                quantity=1,
            )
        ),

        session_start_price=(
            Decimal("300")
        ),

        grid_step=(
            Decimal("1")
        ),
    )

    if with_position:
        engine.open_positions[1] = (
            OpenLevelPosition(
                level_index=1,

                entry_price=(
                    Decimal(
                        "298.70"
                    )
                ),

                quantity=1,

                buy_commission=(
                    Decimal("0.30")
                ),

                expected_sell_commission_percent=(
                    Decimal("0.05")
                ),

                hard_take_profit_price=(
                    Decimal(
                        "299.30"
                    )
                ),

                purchase_cost=(
                    Decimal(
                        "299.00"
                    )
                ),
            )
        )

    return engine


def create_manager(
    engine: GridEngine,
) -> LiveOrderManager:
    return LiveOrderManager(
        account_id="account-1",

        order_executor=(
            FakeOrderExecutor()
        ),
    )


def make_entry_pending(
    engine: GridEngine,
) -> None:
    level = engine.levels[1]

    level.status = (
        GridLevelStatus
        .ORDER_PLACED
    )

    level.trailing_entry = (
        TrailingEntryState(
            level_price=(
                Decimal(
                    "298"
                )
            ),

            lowest_price=(
                Decimal(
                    "297.90"
                )
            ),
        )
    )


def make_exit_pending(
    engine: GridEngine,
) -> None:
    level = engine.levels[0]

    level.status = (
        GridLevelStatus
        .ORDER_PLACED
    )


def test_phantom_entry_level_reverted_to_waiting_price(
) -> None:
    engine = create_engine()

    manager = create_manager(
        engine,
    )

    make_entry_pending(
        engine,
    )

    result = (
        BrokerOrderReconciler()
        .reconcile_instrument(
            engine=engine,
            manager=manager,
            broker_orders=[],
        )
    )

    assert (
        engine.levels[1].status
        == GridLevelStatus
        .WAITING_PRICE
    )

    assert (
        engine
        .levels[1]
        .trailing_entry
        is None
    )

    assert (
        result
        .reverted_entry_levels
        == 1
    )

    assert (
        result.adopted_orders
        == 0
    )


def test_phantom_exit_level_reverted_to_position_opened(
) -> None:
    engine = create_engine(
        with_position=True,
    )

    manager = create_manager(
        engine,
    )

    make_exit_pending(
        engine,
    )

    result = (
        BrokerOrderReconciler()
        .reconcile_instrument(
            engine=engine,
            manager=manager,
            broker_orders=[],
        )
    )

    assert (
        engine.levels[0].status
        == GridLevelStatus
        .POSITION_OPENED
    )

    assert (
        result
        .reverted_exit_levels
        == 1
    )

    assert (
        1
        in engine.open_positions
    )


def test_broker_buy_order_adopted_for_pending_entry(
) -> None:
    engine = create_engine()

    manager = create_manager(
        engine,
    )

    make_entry_pending(
        engine,
    )

    result = (
        BrokerOrderReconciler()
        .reconcile_instrument(
            engine=engine,
            manager=manager,
            broker_orders=[
                BrokerActiveOrder(
                    order_id=(
                        "broker-100"
                    ),

                    instrument_id=(
                        "SBER"
                    ),

                    direction="BUY",

                    quantity_lots=1,

                    price=Decimal(
                        "297.95"
                    ),
                )
            ],
        )
    )

    assert (
        result.adopted_orders
        == 1
    )

    assert (
        result
        .reverted_entry_levels
        == 0
    )

    assert (
        engine.levels[1].status
        == GridLevelStatus
        .ORDER_PLACED
    )

    record = (
        manager
        .active_orders[
            "broker-100"
        ]
    )

    assert isinstance(
        record.command,
        PlaceBuyLimitCommand,
    )

    assert (
        record
        .command
        .level_index
        == 2
    )

    assert (
        record
        .command
        .price
        == Decimal(
            "297.95"
        )
    )


def test_broker_sell_order_adopted_for_pending_exit(
) -> None:
    engine = create_engine(
        with_position=True,
    )

    manager = create_manager(
        engine,
    )

    make_exit_pending(
        engine,
    )

    result = (
        BrokerOrderReconciler()
        .reconcile_instrument(
            engine=engine,
            manager=manager,
            broker_orders=[
                BrokerActiveOrder(
                    order_id=(
                        "broker-200"
                    ),

                    instrument_id=(
                        "SBER"
                    ),

                    direction="SELL",

                    quantity_lots=1,

                    price=Decimal(
                        "299.40"
                    ),
                )
            ],
        )
    )

    assert (
        result.adopted_orders
        == 1
    )

    record = (
        manager
        .active_orders[
            "broker-200"
        ]
    )

    assert isinstance(
        record.command,
        PlaceSellLimitCommand,
    )

    assert (
        record
        .command
        .level_index
        == 1
    )


def test_tracked_order_left_untouched(
) -> None:
    engine = create_engine()

    manager = create_manager(
        engine,
    )

    make_entry_pending(
        engine,
    )

    manager.active_orders[
        "tracked-1"
    ] = LiveOrderRecord(
        command=(
            PlaceBuyLimitCommand(
                instrument_id=(
                    "SBER"
                ),

                level_index=2,

                quantity=1,

                price=Decimal(
                    "297.95"
                ),
            )
        ),

        placed_order=(
            PlacedOrder(
                order_id=(
                    "tracked-1"
                ),
            )
        ),
    )

    result = (
        BrokerOrderReconciler()
        .reconcile_instrument(
            engine=engine,
            manager=manager,
            broker_orders=[],
        )
    )

    assert (
        result.adopted_orders
        == 0
    )

    assert (
        result
        .reverted_entry_levels
        == 0
    )

    assert (
        engine.levels[1].status
        == GridLevelStatus
        .ORDER_PLACED
    )

    assert (
        "tracked-1"
        in manager.active_orders
    )


def test_unknown_broker_order_counted(
) -> None:
    engine = create_engine()

    manager = create_manager(
        engine,
    )

    result = (
        BrokerOrderReconciler()
        .reconcile_instrument(
            engine=engine,
            manager=manager,
            broker_orders=[
                BrokerActiveOrder(
                    order_id=(
                        "broker-300"
                    ),

                    instrument_id=(
                        "SBER"
                    ),

                    direction="BUY",

                    quantity_lots=1,

                    price=Decimal(
                        "250"
                    ),
                )
            ],
        )
    )

    assert (
        result
        .unknown_broker_orders
        == 1
    )

    assert (
        "broker-300"
        not in (
            manager
            .active_orders
        )
    )
