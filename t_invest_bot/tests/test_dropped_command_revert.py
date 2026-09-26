from decimal import Decimal

from application.multi_instrument_sandbox_session import (
    MultiInstrumentSandboxSession,
)
from application.sandbox_trading_session import (
    SandboxTradingSession,
)
from broker.live_order_manager import (
    LiveOrderManager,
)
from domain.commands import (
    PlaceSellAllLimitCommand,
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
    TrailingExitState,
)


class PlainFakeExecutor:
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


class GuardedExecutor(
    PlainFakeExecutor,
):
    """
    Имитирует «КРИТИЧЕСКУЮ ЗАЩИТУ
    LIVE»: у брокера уже есть
    активная заявка по инструменту.
    """

    def has_active_order(
        self,
        account_id: str,
        instrument_id: str,
    ) -> bool:
        return True


class ListingExecutor(
    PlainFakeExecutor,
):
    def __init__(
        self,
        orders: list[
            BrokerActiveOrder
        ],
    ) -> None:
        self.orders = orders
        self.list_calls = 0

    def list_active_orders(
        self,
        account_id: str,
    ) -> list[
        BrokerActiveOrder
    ]:
        self.list_calls += 1

        return self.orders


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
                    Decimal("0")
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
                        "298.70"
                    )
                ),

                trailing_exit=(
                    TrailingExitState(
                        target_price=(
                            Decimal(
                                "299.30"
                            )
                        ),

                        highest_price=(
                            Decimal(
                                "300"
                            )
                        ),

                        is_confirmed=(
                            True
                        ),
                    )
                ),
            )
        )

        engine.levels[0].status = (
            GridLevelStatus
            .POSITION_OPENED
        )

    return engine


def test_dropped_sell_command_reverts_level_to_position_opened(
) -> None:
    engine = create_engine(
        with_position=True,
    )

    manager = LiveOrderManager(
        account_id="account-1",

        order_executor=(
            GuardedExecutor()
        ),
    )

    session = (
        SandboxTradingSession(
            grid_engine=engine,

            live_order_manager=(
                manager
            ),
        )
    )

    placed_orders = (
        session.on_price(
            Decimal("300")
        )
    )

    level = engine.levels[0]

    assert (
        placed_orders
        == []
    )

    assert (
        level.status
        == GridLevelStatus
        .POSITION_OPENED
    )

    assert (
        manager.active_orders
        == {}
    )

    assert (
        1
        in engine.open_positions
    )


def test_dropped_buy_command_reverts_level(
) -> None:
    engine = create_engine()

    manager = LiveOrderManager(
        account_id="account-1",

        order_executor=(
            GuardedExecutor()
        ),
    )

    session = (
        SandboxTradingSession(
            grid_engine=engine,

            live_order_manager=(
                manager
            ),
        )
    )

    level = engine.levels[0]

    session.on_price(
        Decimal("298.50")
    )

    trigger_price = (
        level
        .trailing_entry
        .trigger_price
    )

    placed_orders = (
        session.on_price(
            trigger_price
        )
    )

    assert (
        placed_orders
        == []
    )

    assert (
        level.status
        == GridLevelStatus
        .WAITING_PRICE
    )

    assert (
        level.trailing_entry
        is None
    )

    assert (
        manager.active_orders
        == {}
    )


def test_dropped_compensation_resets_pending_flag(
) -> None:
    engine = create_engine()

    manager = LiveOrderManager(
        account_id="account-1",

        order_executor=(
            GuardedExecutor()
        ),
    )

    session = (
        SandboxTradingSession(
            grid_engine=engine,

            live_order_manager=(
                manager
            ),
        )
    )

    engine\
        .risk_manager\
        .compensation_order_pending = (
            True
        )

    session\
        ._revert_levels_for_dropped_commands(
            commands=[
                PlaceSellAllLimitCommand(
                    instrument_id=(
                        "SBER"
                    ),

                    quantity=2,

                    price=Decimal(
                        "299"
                    ),
                )
            ],
        )

    assert (
        engine
        .risk_manager
        .compensation_order_pending
        is False
    )


def test_multi_session_reconcile_adopts_broker_order(
) -> None:
    engine = create_engine()

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

    executor = (
        ListingExecutor(
            orders=[
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

    manager = LiveOrderManager(
        account_id="account-1",

        order_executor=(
            executor
        ),
    )

    session = (
        SandboxTradingSession(
            grid_engine=engine,

            live_order_manager=(
                manager
            ),
        )
    )

    multi_session = (
        MultiInstrumentSandboxSession(
            sessions={
                "SBER": session,
            },
        )
    )

    results = (
        multi_session
        .reconcile_broker_orders()
    )

    assert (
        len(results)
        == 1
    )

    assert (
        results[0]
        .adopted_orders
        == 1
    )

    assert (
        executor.list_calls
        == 1
    )

    assert (
        "broker-100"
        in manager.active_orders
    )


def test_multi_session_reconcile_skipped_for_sandbox_executor(
) -> None:
    engine = create_engine()

    manager = LiveOrderManager(
        account_id="account-1",

        order_executor=(
            PlainFakeExecutor()
        ),
    )

    session = (
        SandboxTradingSession(
            grid_engine=engine,

            live_order_manager=(
                manager
            ),
        )
    )

    multi_session = (
        MultiInstrumentSandboxSession(
            sessions={
                "SBER": session,
            },
        )
    )

    results = (
        multi_session
        .reconcile_broker_orders()
    )

    assert (
        results
        == []
    )
