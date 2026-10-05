from decimal import Decimal

from application.broker_position_reconciler import (
    BrokerPositionReconciler,
)
from broker.live_order_manager import (
    LiveOrderManager,
    LiveOrderRecord,
)
from domain.commands import (
    PlaceSellLimitCommand,
)
from domain.enums import (
    GridLevelStatus,
)
from domain.order_execution import (
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


class FakeBrokerPosition:
    def __init__(
        self,
        instrument_uid: str,
        quantity_lots: int,
        blocked_lots: int = 0,
    ) -> None:
        self.instrument_uid = (
            instrument_uid
        )

        self.quantity_lots = (
            quantity_lots
        )

        self.blocked_lots = (
            blocked_lots
        )


class FakePositionProvider:
    def __init__(
        self,
        positions: list[
            FakeBrokerPosition
        ],
    ) -> None:
        self.positions = (
            positions
        )

    def get_positions(
        self,
        account_id: str,
    ) -> list[
        FakeBrokerPosition
    ]:
        return self.positions


def create_session(
    instrument_id: str = "SBER",
    with_positions: bool = True,
):
    engine = GridEngine(
        instrument_id=(
            instrument_id
        ),

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

    if with_positions:
        for index in (1, 2):
            engine.open_positions[
                index
            ] = OpenLevelPosition(
                level_index=(
                    index
                ),

                entry_price=(
                    Decimal(
                        "298"
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
                        "298.50"
                    )
                ),

                purchase_cost=(
                    Decimal(
                        "298"
                    )
                ),
            )

            engine.levels[
                index - 1
            ].status = (
                GridLevelStatus
                .POSITION_OPENED
            )

    manager = LiveOrderManager(
        account_id="account-1",

        order_executor=(
            FakeOrderExecutor()
        ),
    )

    class TradingSession:
        grid_engine = engine
        live_order_manager = manager

    return TradingSession()


def test_vanished_positions_cleared_and_levels_released(
) -> None:
    session = (
        create_session()
    )

    engine = (
        session.grid_engine
    )

    provider = (
        FakePositionProvider(
            positions=[],
        )
    )

    report = (
        BrokerPositionReconciler()
        .reconcile(
            sessions={
                "SBER": session,
            },

            account_id=(
                "account-1"
            ),

            position_provider=(
                provider
            ),
        )
    )

    assert (
        engine.open_positions
        == {}
    )

    assert (
        engine.levels[0].status
        == GridLevelStatus
        .WAITING_PRICE
    )

    assert (
        engine.levels[1].status
        == GridLevelStatus
        .WAITING_PRICE
    )

    assert (
        report.instruments_cleared
        == ["SBER"]
    )


def test_positions_present_left_untouched(
) -> None:
    session = (
        create_session()
    )

    engine = (
        session.grid_engine
    )

    provider = (
        FakePositionProvider(
            positions=[
                FakeBrokerPosition(
                    instrument_uid=(
                        "SBER"
                    ),

                    quantity_lots=2,
                ),
            ],
        )
    )

    report = (
        BrokerPositionReconciler()
        .reconcile(
            sessions={
                "SBER": session,
            },

            account_id=(
                "account-1"
            ),

            position_provider=(
                provider
            ),
        )
    )

    assert (
        len(
            engine
            .open_positions
        )
        == 2
    )

    assert (
        report.instruments_cleared
        == []
    )

    assert (
        report.mismatch_warnings
        == []
    )


def test_partial_mismatch_reported_only(
) -> None:
    session = (
        create_session()
    )

    engine = (
        session.grid_engine
    )

    provider = (
        FakePositionProvider(
            positions=[
                FakeBrokerPosition(
                    instrument_uid=(
                        "SBER"
                    ),

                    quantity_lots=1,
                ),
            ],
        )
    )

    report = (
        BrokerPositionReconciler()
        .reconcile(
            sessions={
                "SBER": session,
            },

            account_id=(
                "account-1"
            ),

            position_provider=(
                provider
            ),
        )
    )

    assert (
        len(
            engine
            .open_positions
        )
        == 2
    )

    assert (
        len(
            report
            .mismatch_warnings
        )
        == 1
    )

    assert (
        report.instruments_cleared
        == []
    )


def test_blocked_lots_prevent_clearing(
) -> None:
    session = (
        create_session()
    )

    engine = (
        session.grid_engine
    )

    provider = (
        FakePositionProvider(
            positions=[
                FakeBrokerPosition(
                    instrument_uid=(
                        "SBER"
                    ),

                    quantity_lots=0,

                    blocked_lots=1,
                ),
            ],
        )
    )

    report = (
        BrokerPositionReconciler()
        .reconcile(
            sessions={
                "SBER": session,
            },

            account_id=(
                "account-1"
            ),

            position_provider=(
                provider
            ),
        )
    )

    assert (
        len(
            engine
            .open_positions
        )
        == 2
    )

    assert (
        report.instruments_cleared
        == []
    )


def test_tracked_sell_order_prevents_clearing(
) -> None:
    session = (
        create_session()
    )

    engine = (
        session.grid_engine
    )

    session\
        .live_order_manager\
        .active_orders[
            "sell-1"
        ] = LiveOrderRecord(
            command=(
                PlaceSellLimitCommand(
                    instrument_id=(
                        "SBER"
                    ),

                    level_index=1,

                    quantity=1,

                    price=Decimal(
                        "299"
                    ),
                )
            ),

            placed_order=(
                PlacedOrder(
                    order_id=(
                        "sell-1"
                    ),
                )
            ),
        )

    provider = (
        FakePositionProvider(
            positions=[],
        )
    )

    report = (
        BrokerPositionReconciler()
        .reconcile(
            sessions={
                "SBER": session,
            },

            account_id=(
                "account-1"
            ),

            position_provider=(
                provider
            ),
        )
    )

    assert (
        len(
            engine
            .open_positions
        )
        == 2
    )

    assert (
        report.instruments_cleared
        == []
    )


def test_engine_without_positions_skipped(
) -> None:
    session = (
        create_session(
            with_positions=False,
        )
    )

    provider = (
        FakePositionProvider(
            positions=[],
        )
    )

    report = (
        BrokerPositionReconciler()
        .reconcile(
            sessions={
                "SBER": session,
            },

            account_id=(
                "account-1"
            ),

            position_provider=(
                provider
            ),
        )
    )

    assert (
        report.instruments_cleared
        == []
    )

    assert (
        report.mismatch_warnings
        == []
    )


def test_cleared_purchase_cost_reported(
) -> None:
    session = (
        create_session()
    )

    provider = (
        FakePositionProvider(
            positions=[],
        )
    )

    report = (
        BrokerPositionReconciler()
        .reconcile(
            sessions={
                "SBER": session,
            },

            account_id=(
                "account-1"
            ),

            position_provider=(
                provider
            ),
        )
    )

    assert (
        report
        .cleared_purchase_cost
        == {
            "SBER": (
                Decimal("596")
            ),
        }
    )
