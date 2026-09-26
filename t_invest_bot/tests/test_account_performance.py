from __future__ import annotations

from decimal import (
    Decimal,
)
from pathlib import Path

from application.account_performance_service import (
    AccountPerformanceService,
)

from domain.money_movement import (
    MoneyMovement,
)

from domain.trading_state import (
    GridLevelState,
    InstrumentTradingState,
    OpenPositionState,
    TradingSessionState,
)

from infrastructure.sqlite.money_movement_repository import (
    SQLiteMoneyMovementRepository,
)
from infrastructure.sqlite.sqlite_database import (
    SQLiteDatabase,
)
from infrastructure.sqlite.trading_state_repository import (
    TradingStateRepository,
)


class FakeMovementRepository:
    def __init__(
        self,
        movements,
    ) -> None:
        self.movements = (
            movements
        )

    def get_by_account(
        self,
        trading_account_id: str,
    ):
        return [
            movement

            for movement
            in (
                self
                .movements
            )

            if (
                movement
                .trading_account_id
                == trading_account_id
            )
        ]


class FakeStateRepository:
    def __init__(
        self,
        states,
    ) -> None:
        self.states = (
            states
        )

    def get_all(
        self,
    ):
        return (
            self
            .states
        )


def make_movement(
    amount: str,
    trading_account_id: str = (
        "tinvest:acc-1"
    ),
) -> MoneyMovement:
    return (
        MoneyMovement(
            created_at=(
                "2026-09-26T10:00:00"
                "+00:00"
            ),

            trading_account_id=(
                trading_account_id
            ),

            amount=Decimal(
                amount
            ),
        )
    )


def make_state(
    trading_account_id: str,
    realized: str,
    with_position: bool = (
        True
    ),
    current_price: (
        str | None
    ) = "110",
) -> TradingSessionState:
    instrument = (
        InstrumentTradingState(
            ticker="SBER",
            instrument_uid=(
                "uid-SBER"
            ),
            current_price=(
                Decimal(
                    current_price
                )

                if (
                    current_price
                    is not None
                )

                else None
            ),

            realized_profit=Decimal(
                realized
            ),

            levels=[
                GridLevelState(
                    level_index=0,
                    level_price=Decimal(
                        "100"
                    ),
                    status=(
                        "POSITION_OPENED"
                    ),
                )
            ],

            open_positions=(
                [
                    OpenPositionState(
                        level_index=0,
                        entry_price=Decimal(
                            "100"
                        ),
                        quantity=2,
                        buy_commission=Decimal(
                            "0.3"
                        ),
                        hard_take_profit_price=Decimal(
                            "105"
                        ),
                        expected_sell_commission_percent=(
                            Decimal(
                                "0.3"
                            )
                        ),
                    )
                ]

                if with_position

                else []
            ),
        )
    )

    return (
        TradingSessionState(
            schema_version=4,
            session_id=(
                "sandbox:acct:1"
            ),
            trading_account_id=(
                trading_account_id
            ),
            broker_account_id=(
                "sbx-broker-1"
            ),
            mode="live",
            status="STOPPED",
            available_cash=Decimal(
                "0"
            ),
            reserved_cash=Decimal(
                "0"
            ),
            instruments=[
                instrument
            ],
        )
    )


def test_performance_calculates_balance_and_roi() -> None:
    service = (
        AccountPerformanceService(
            movement_repository=(
                FakeMovementRepository(
                    [
                        make_movement(
                            "100000"
                        ),

                        make_movement(
                            "-30000"
                        ),
                    ]
                )
            ),

            state_repository=(
                FakeStateRepository(
                    [
                        make_state(
                            trading_account_id=(
                                "tinvest:acc-1"
                            ),

                            realized=(
                                "500"
                            ),
                        )
                    ]
                )
            ),
        )
    )

    report = (
        service
        .build_report(
            trading_account_id=(
                "tinvest:acc-1"
            )
        )
    )

    assert (
        report
        .deposits_total
        == Decimal(
            "100000"
        )
    )

    assert (
        report
        .withdrawals_total
        == Decimal(
            "30000"
        )
    )

    assert (
        report
        .net_deposits
        == Decimal(
            "70000"
        )
    )

    # unrealized = (110 - 100) * 2 = 20
    assert (
        report
        .unrealized_profit
        == Decimal(
            "20"
        )
    )

    assert (
        report
        .unrealized_estimated
        is False
    )

    assert (
        report
        .historical_balance
        == Decimal(
            "70520"
        )
    )

    # open_invested: purchase_cost отсутствует -> 100 * 2 = 200
    assert (
        report
        .open_invested
        == Decimal(
            "200"
        )
    )

    #
    # ROE = (500 + 20) / 100000 * 100
    # (к сумме ВСЕХ пополнений,
    # выводы не вычитаются).
    #
    assert (
        report
        .roe_percent
        == (
            Decimal(
                "520"
            )
            / Decimal(
                "100000"
            )
            * Decimal(
                "100"
            )
        )
    )

    #
    # ROI = открытые позиции
    # / текущий баланс.
    #
    assert (
        report
        .roi_percent
        == (
            Decimal(
                "200"
            )
            / Decimal(
                "70520"
            )
            * Decimal(
                "100"
            )
        )
    )


def test_performance_matches_legacy_snapshots_by_broker_account() -> None:
    service = (
        AccountPerformanceService(
            movement_repository=(
                FakeMovementRepository(
                    [
                        make_movement(
                            "50000"
                        ),
                    ]
                )
            ),

            state_repository=(
                FakeStateRepository(
                    [
                        make_state(
                            trading_account_id=(
                                "live:legacy-id"
                            ),

                            realized=(
                                "100"
                            ),

                            with_position=(
                                False
                            ),
                        )
                    ]
                )
            ),
        )
    )

    report = (
        service
        .build_report(
            trading_account_id=(
                "tinvest:acc-1"
            ),

            broker_account_id=(
                "sbx-broker-1"
            ),
        )
    )

    assert (
        report
        .realized_profit
        == Decimal(
            "100"
        )
    )

    assert (
        report
        .historical_balance
        == Decimal(
            "50100"
        )
    )


def test_performance_roi_none_without_deposits() -> None:
    service = (
        AccountPerformanceService(
            movement_repository=(
                FakeMovementRepository(
                    []
                )
            ),

            state_repository=(
                FakeStateRepository(
                    []
                )
            ),
        )
    )

    report = (
        service
        .build_report(
            trading_account_id=(
                "tinvest:acc-1"
            )
        )
    )

    assert (
        report
        .net_deposits
        == 0
    )

    assert (
        report
        .roe_percent
        is None
    )

    assert (
        report
        .roi_percent
        is None
    )


def test_money_movement_repository_roundtrip(
    tmp_path: Path,
) -> None:
    database = (
        SQLiteDatabase(
            database_path=(
                tmp_path
                / "test.db"
            ),
        )
    )

    database.initialize()

    repository = (
        SQLiteMoneyMovementRepository(
            database=database,
        )
    )

    repository.record(
        make_movement(
            "1000"
        )
    )

    repository.record(
        make_movement(
            "-250"
        )
    )

    movements = (
        repository
        .get_by_account(
            "tinvest:acc-1"
        )
    )

    assert (
        len(
            movements
        )
        == 2
    )

    #
    # Свежие записи первыми.
    #
    assert (
        movements[
            0
        ]
        .amount
        == Decimal(
            "-250"
        )
    )

    assert (
        movements[
            1
        ]
        .amount
        == Decimal(
            "1000"
        )
    )

    other = (
        repository
        .get_by_account(
            "tinvest:acc-2"
        )
    )

    assert (
        other
        == []
    )


def test_money_movement_repository_creates_table_once(
    tmp_path: Path,
) -> None:
    database = (
        SQLiteDatabase(
            database_path=(
                tmp_path
                / "test.db"
            ),
        )
    )

    database.initialize()

    repository = (
        SQLiteMoneyMovementRepository(
            database=database,
        )
    )

    repository.record(
        MoneyMovement(
            created_at=(
                "2026-09-26T10:00:00"
                "+00:00"
            ),

            trading_account_id=(
                "tinvest:acc-9"
            ),

            amount=Decimal(
                "10"
            ),

            note="тест",
        )
    )

    database.initialize()

    movements = (
        repository
        .get_by_account(
            "tinvest:acc-9"
        )
    )

    assert (
        len(
            movements
        )
        == 1
    )

    assert (
        movements[
            0
        ]
        .note
        == "тест"
    )
