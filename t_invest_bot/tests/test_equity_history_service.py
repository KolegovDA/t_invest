from datetime import (
    datetime,
    timedelta,
    timezone,
)
from decimal import Decimal

from application.equity_history_service import (
    EquityHistoryService,
)
from domain.broker_cash_flow import (
    BrokerCashFlow,
)
from domain.money_movement import (
    MoneyMovement,
)
from domain.operation_event import (
    OperationEvent,
)


now = datetime.now(
    timezone.utc,
)


class FakeOperationLogRepository:
    def __init__(
        self,
        events,
    ):
        self.events = (
            events
        )

    def get_since(
        self,
        since,
        event_types=None,
    ):
        return (
            self
            .events
        )


class FakeMoneyMovementRepository:
    def __init__(
        self,
        movements,
    ):
        self.movements = (
            movements
        )

    def get_since(
        self,
        since,
    ):
        return (
            self
            .movements
        )


class FakeBrokerCashFlowRepository:
    def __init__(
        self,
        flows,
    ):
        self.flows = (
            flows
        )

    def get_since(
        self,
        since,
    ):
        return (
            self
            .flows
        )


def cash_flow(
    occurred_at: datetime,
    payment: str,
    kind: str = "input",
    currency: str = "RUB",
    trading_account_id: str = "account-1",
) -> BrokerCashFlow:
    return (
        BrokerCashFlow(
            trading_account_id=(
                trading_account_id
            ),

            occurred_at=(
                occurred_at
                .isoformat()
            ),

            kind=kind,

            currency=currency,

            payment=Decimal(
                payment
            ),
        )
    )


def make_service(
    events=(),
    movements=(),
    flows=(),
) -> EquityHistoryService:
    return (
        EquityHistoryService(
            operation_log_repository=(
                FakeOperationLogRepository(
                    list(
                        events
                    )
                )
            ),

            money_movement_repository=(
                FakeMoneyMovementRepository(
                    list(
                        movements
                    )
                )
            ),

            broker_cash_flow_repository=(
                FakeBrokerCashFlowRepository(
                    list(
                        flows
                    )
                )
            ),
        )
    )


def sell_event(
    created_at: datetime,
    profit: str,
    trading_account_id: (
        str | None
    ) = None,
) -> OperationEvent:
    return (
        OperationEvent(
            created_at=(
                created_at
                .isoformat()
            ),

            event_type=(
                "SELL"
            ),

            trading_account_id=(
                trading_account_id
            ),

            details=(
                "уровень=1 кол-во=10 "
                "цена=100.50 комиссия=1.00 "
                f"прибыль={profit}"
            ),
        )
    )


def movement(
    created_at: datetime,
    amount: str,
) -> MoneyMovement:
    return (
        MoneyMovement(
            id=1,

            created_at=(
                created_at
                .isoformat()
            ),

            trading_account_id=(
                "account-1"
            ),

            amount=Decimal(
                amount
            ),

            note=(
                "Пополнение"
            ),
        )
    )


def test_build_reconstructs_equity_curve():
    service = (
        make_service(
            events=[
                sell_event(
                    now
                    - timedelta(
                        days=3,
                    ),

                    "10",
                ),

                sell_event(
                    now
                    - timedelta(
                        days=1,
                    ),

                    "5",
                ),
            ],

            movements=[
                movement(
                    now
                    - timedelta(
                        days=2,
                    ),

                    "50",
                ),
            ],
        )
    )

    result = (
        service
        .build(
            current_equity=(
                Decimal(
                    "170"
                )
            ),

            days=7,
        )
    )

    equities = [
        point[
            "equity"
        ]
        for point
        in result[
            "points"
        ]
    ]

    assert (
        equities
        == [
            105.0,
            115.0,
            165.0,
            170.0,
            170.0,
        ]
    )


def test_build_computes_today_pnl_without_movements():
    service = (
        make_service(
            events=[
                sell_event(
                    now
                    - timedelta(
                        hours=2,
                    ),

                    "20",
                ),
            ],

            movements=[
                movement(
                    now
                    - timedelta(
                        hours=1,
                    ),

                    "50",
                ),
            ],
        )
    )

    result = (
        service
        .build(
            current_equity=(
                Decimal(
                    "170"
                )
            ),

            days=7,
        )
    )

    assert (
        result[
            "pnl_today"
        ]
        == 20.0
    )

    assert (
        result[
            "pnl_today_percent"
        ]
        == 20.0
    )


def test_build_normalizes_days():
    service = (
        make_service()
    )

    result = (
        service
        .build(
            current_equity=(
                Decimal(
                    "100"
                )
            ),

            days=15,
        )
    )

    assert (
        result[
            "days"
        ]
        == 7
    )

    assert (
        len(
            result[
                "points"
            ]
        )
        == 2
    )


def test_build_skips_events_without_profit():
    event = (
        OperationEvent(
            created_at=(
                now
                .isoformat()
            ),

            event_type=(
                "SELL"
            ),

            details=(
                "уровень=1 кол-во=10 "
                "цена=100.50 комиссия=1.00"
            ),
        )
    )

    service = (
        make_service(
            events=[
                event,
            ],
        )
    )

    result = (
        service
        .build(
            current_equity=(
                Decimal(
                    "100"
                )
            ),

            days=7,
        )
    )

    assert (
        result[
            "points"
        ][
            0
        ][
            "equity"
        ]
        == 100.0
    )

    assert (
        result[
            "pnl_today"
        ]
        == 0.0
    )


def test_build_splits_points_by_currency():
    service = (
        make_service(
            events=[
                sell_event(
                    now
                    - timedelta(
                        days=1,
                    ),

                    "10",

                    "tinkoff-1",
                ),

                sell_event(
                    now
                    - timedelta(
                        days=1,
                    ),

                    "4",

                    "bybit-1",
                ),
            ],
        )
    )

    result = (
        service
        .build(
            current_equity=(
                Decimal(
                    "120"
                )
            ),

            days=7,

            current_equity_by_currency={
                "RUB": (
                    Decimal(
                        "110"
                    )
                ),

                "USDT": (
                    Decimal(
                        "10"
                    )
                ),
            },

            account_currency_by_id={
                "tinkoff-1": (
                    "RUB"
                ),

                "bybit-1": (
                    "USDT"
                ),
            },
        )
    )

    assert (
        set(
            result[
                "points_by_currency"
            ]
        )
        == {
            "RUB",
            "USDT",
        }
    )

    assert (
        [
            point[
                "equity"
            ]

            for point
            in result[
                "points_by_currency"
            ][
                "RUB"
            ]
        ]
        == [
            100.0,
            110.0,
            110.0,
        ]
    )

    assert (
        [
            point[
                "equity"
            ]

            for point
            in result[
                "points_by_currency"
            ][
                "USDT"
            ]
        ]
        == [
            6.0,
            10.0,
            10.0,
        ]
    )

    assert (
        result[
            "equity_by_currency"
        ]
        == {
            "RUB": 110.0,
            "USDT": 10.0,
        }
    )


def test_build_uses_snapshots_when_provided():
    service = (
        make_service(
            events=[
                sell_event(
                    now
                    - timedelta(
                        days=1,
                    ),

                    "10",
                ),
            ],
        )
    )

    result = (
        service
        .build(
            current_equity=(
                Decimal(
                    "155"
                )
            ),

            days=7,

            current_equity_by_currency={
                "RUB": (
                    Decimal(
                        "105"
                    )
                ),

                "USDT": (
                    Decimal(
                        "50"
                    )
                ),
            },

            snapshots_by_currency={
                "RUB": [
                    (
                        now
                        - timedelta(
                            hours=2,
                        ),

                        Decimal(
                            "100"
                        ),
                    ),

                    (
                        now
                        - timedelta(
                            hours=1,
                        ),

                        Decimal(
                            "105"
                        ),
                    ),
                ],

                "USDT": [
                    (
                        now
                        - timedelta(
                            hours=2,
                        ),

                        Decimal(
                            "50"
                        ),
                    ),
                ],
            },
        )
    )

    assert (
        [
            point[
                "equity"
            ]

            for point
            in result[
                "points_by_currency"
            ][
                "RUB"
            ]
        ]
        == [
            95.0,

            105.0,

            100.0,

            105.0,

            105.0,
        ]
    )

    assert (
        [
            point[
                "equity"
            ]

            for point
            in result[
                "points_by_currency"
            ][
                "USDT"
            ]
        ]
        == [
            50.0,

            50.0,

            50.0,
        ]
    )

    assert (
        result[
            "equity_by_currency"
        ]
        == {
            "RUB": 105.0,
            "USDT": 50.0,
        }
    )

    assert (
        [
            point[
                "equity"
            ]

            for point
            in result[
                "points"
            ]
        ]
        == [
            145.0,

            155.0,

            155.0,
        ]
    )


def test_build_ignores_snapshots_older_than_window():
    service = (
        make_service()
    )

    result = (
        service
        .build(
            current_equity=(
                Decimal(
                    "100"
                )
            ),

            days=7,

            current_equity_by_currency={
                "RUB": (
                    Decimal(
                        "100"
                    )
                ),
            },

            snapshots_by_currency={
                "RUB": [
                    (
                        now
                        - timedelta(
                            days=30,
                        ),

                        Decimal(
                            "70"
                        ),
                    ),

                    (
                        now
                        - timedelta(
                            days=1,
                        ),

                        Decimal(
                            "90"
                        ),
                    ),
                ],
            },
        )
    )

    assert (
        [
            point[
                "equity"
            ]

            for point
            in result[
                "points_by_currency"
            ][
                "RUB"
            ]
        ]
        == [
            100.0,

            90.0,

            100.0,
        ]
    )

    assert (
        result[
            "equity_by_currency"
        ]
        == {
            "RUB": 100.0,
        }
    )


def test_pnl_today_by_account_groups_profits() -> None:
    service = (
        make_service(
            events=[
                sell_event(
                    now
                    - timedelta(
                        hours=2,
                    ),

                    "5.00",

                    "account-1",
                ),

                sell_event(
                    now
                    - timedelta(
                        hours=1,
                    ),

                    "3.50",

                    "account-1",
                ),

                sell_event(
                    now
                    - timedelta(
                        hours=1,
                    ),

                    "2.00",

                    "account-2",
                ),
            ],
        )
    )

    assert (
        service
        .pnl_today_by_account()
        == {
            "account-1": (
                Decimal(
                    "8.50",
                )
            ),

            "account-2": (
                Decimal(
                    "2.00",
                )
            ),
        }
    )


def test_build_computes_today_pnl_from_snapshots() -> None:
    today_start = (
        now
        .replace(
            hour=0,

            minute=0,

            second=0,

            microsecond=0,
        )
    )

    service = (
        make_service(
            movements=[
                movement(
                    now
                    - timedelta(
                        hours=1,
                    ),

                    "50",
                ),
            ],
        )
    )

    result = (
        service
        .build(
            current_equity=(
                Decimal(
                    "130"
                )
            ),

            days=7,

            current_equity_by_currency={
                "RUB": (
                    Decimal(
                        "130"
                    )
                ),
            },

            snapshots_by_currency={
                "RUB": [
                    (
                        today_start
                        - timedelta(
                            minutes=10,
                        ),

                        Decimal(
                            "100"
                        ),
                    ),

                    (
                        today_start
                        + timedelta(
                            hours=1,
                        ),

                        Decimal(
                            "120"
                        ),
                    ),
                ],
            },
        )
    )

    assert (
        result[
            "pnl_today"
        ]
        == -20.0
    )

    assert (
        result[
            "pnl_today_percent"
        ]
        == -20.0
    )


def test_build_mixes_snapshot_and_profit_currencies_today() -> None:
    today_start = (
        now
        .replace(
            hour=0,

            minute=0,

            second=0,

            microsecond=0,
        )
    )

    service = (
        make_service(
            events=[
                sell_event(
                    now
                    - timedelta(
                        hours=2,
                    ),

                    "5",

                    "account-2",
                ),
            ],
        )
    )

    result = (
        service
        .build(
            current_equity=(
                Decimal(
                    "120"
                )
            ),

            days=7,

            account_currency_by_id={
                "account-2": (
                    "USDT"
                ),
            },

            current_equity_by_currency={
                "RUB": (
                    Decimal(
                        "85"
                    )
                ),

                "USDT": (
                    Decimal(
                        "35"
                    )
                ),
            },

            snapshots_by_currency={
                "RUB": [
                    (
                        today_start
                        - timedelta(
                            minutes=10,
                        ),

                        Decimal(
                            "70"
                        ),
                    ),

                    (
                        today_start
                        + timedelta(
                            hours=1,
                        ),

                        Decimal(
                            "75"
                        ),
                    ),
                ],
            },
        )
    )

    assert (
        result[
            "pnl_today"
        ]
        == 20.0
    )

    assert (
        result[
            "pnl_today_percent"
        ]
        == 20.0
    )


def test_pnl_today_by_account_prefers_snapshots() -> None:
    today_start = (
        now
        .replace(
            hour=0,

            minute=0,

            second=0,

            microsecond=0,
        )
    )

    service = (
        make_service(
            events=[
                sell_event(
                    now
                    - timedelta(
                        hours=2,
                    ),

                    "5.00",

                    "account-1",
                ),
            ],

            movements=[
                movement(
                    now
                    - timedelta(
                        hours=1,
                    ),

                    "20",
                ),
            ],
        )
    )

    assert (
        service
        .pnl_today_by_account(
            current_equity_by_account={
                "account-1": (
                    Decimal(
                        "130"
                    )
                ),
            },

            snapshots_by_account={
                "account-1": [
                    (
                        today_start
                        - timedelta(
                            minutes=10,
                        ),

                        Decimal(
                            "100"
                        ),
                    ),

                    (
                        today_start
                        + timedelta(
                            hours=2,
                        ),

                        Decimal(
                            "110"
                        ),
                    ),
                ],

                "account-2": [
                    (
                        today_start
                        + timedelta(
                            hours=1,
                        ),

                        Decimal(
                            "40"
                        ),
                    ),
                ],
            },
        )
        == {
            "account-1": (
                Decimal(
                    "10"
                )
            ),
        }
    )


def test_snapshot_points_appends_now_point() -> None:
    service = (
        EquityHistoryService()
    )

    snapshots = [
        (
            now
            - timedelta(
                hours=2,
            ),

            Decimal(
                "100",
            ),
        ),

        (
            now
            - timedelta(
                hours=1,
            ),

            Decimal(
                "110",
            ),
        ),
    ]

    points = (
        service
        .snapshot_points(
            snapshots=(
                snapshots
            ),

            now=now,
        )
    )

    assert (
        [
            point[
                "equity"
            ]

            for point
            in points
        ]
        == [
            100.0,

            110.0,

            110.0,
        ]
    )

    assert (
        points[
            -1
        ][
            "ts"
        ]
        == (
            now
            .isoformat()
        )
    )


def test_pnl_total_from_first_snapshot_and_flows() -> None:
    service = (
        make_service(
            flows=[
                cash_flow(
                    now
                    - timedelta(
                        days=5,
                    ),

                    "1000",
                ),
            ],
        )
    )

    response = (
        service
        .build(
            current_equity=(
                Decimal(
                    "1500"
                )
            ),

            days=7,

            current_equity_by_currency={
                "RUB": (
                    Decimal(
                        "1500"
                    )
                ),
            },

            snapshots_by_currency={
                "RUB": [
                    (
                        now
                        - timedelta(
                            days=6,
                        ),

                        Decimal(
                            "500"
                        ),
                    ),

                    (
                        now,

                        Decimal(
                            "1500"
                        ),
                    ),
                ],
            },

            first_snapshot_by_currency={
                "RUB": (
                    now
                    - timedelta(
                        days=6,
                    ),

                    Decimal(
                        "500"
                    ),
                ),
            },
        )
    )

    assert (
        response[
            "pnl_total"
        ]
        == 0.0
    )

    assert (
        response[
            "pnl_total_percent"
        ]
        == 0.0
    )


def test_pnl_total_with_movements() -> None:
    service = (
        make_service(
            movements=[
                movement(
                    now
                    - timedelta(
                        days=5,
                    ),

                    "500",
                ),
            ],
        )
    )

    response = (
        service
        .build(
            current_equity=(
                Decimal(
                    "1800"
                )
            ),

            days=7,

            first_snapshot_by_currency={
                "RUB": (
                    now
                    - timedelta(
                        days=10,
                    ),

                    Decimal(
                        "1000"
                    ),
                ),
            },
        )
    )

    assert (
        response[
            "pnl_total"
        ]
        == 300.0
    )

    assert (
        response[
            "pnl_total_percent"
        ]
        == 30.0
    )


def test_account_pnl_excludes_broker_withdrawals() -> None:
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    service = make_service(
        flows=[
            cash_flow(today_start + timedelta(seconds=1), "-40", kind="output"),
            cash_flow(
                today_start + timedelta(seconds=1),
                "100",
                trading_account_id="account-2",
            ),
        ],
    )

    result = service.pnl_today_by_account(
        current_equity_by_account={"account-1": Decimal("65")},
        snapshots_by_account={
            "account-1": [(today_start - timedelta(minutes=1), Decimal("100"))],
        },
    )

    assert result == {"account-1": Decimal("5")}


def test_snapshot_points_uses_current_broker_balance() -> None:
    service = make_service()
    points = service.snapshot_points(
        snapshots=[(now - timedelta(hours=1), Decimal("100"))],
        now=now,
        current_equity=Decimal("60"),
    )

    assert points[-1] == {"ts": now.isoformat(), "equity": 60.0}
    assert service.snapshot_points(snapshots=[], now=now) == []


def test_build_snapshot_pnl_excludes_broker_withdrawal() -> None:
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    service = make_service(
        flows=[cash_flow(today_start + timedelta(seconds=1), "-40", kind="output")],
    )

    result = service.build(
        current_equity=Decimal("65"),
        current_equity_by_currency={"RUB": Decimal("65")},
        snapshots_by_currency={
            "RUB": [(today_start - timedelta(minutes=1), Decimal("100"))],
        },
    )

    assert result["pnl_today"] == 5.0
    assert result["equity_by_currency"] == {"RUB": 65.0}
    assert result["points_by_currency"]["RUB"][-1]["equity"] == 65.0


def test_pnl_total_without_snapshots() -> None:
    service = (
        make_service()
    )

    response = (
        service
        .build(
            current_equity=(
                Decimal(
                    "100"
                )
            ),

            days=7,
        )
    )

    assert (
        response[
            "pnl_total"
        ]

        is None
    )

    assert (
        response[
            "pnl_total_percent"
        ]

        is None
    )
