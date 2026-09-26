from __future__ import annotations

from decimal import (
    Decimal,
)
from pathlib import Path

from application.phantom_position_auditor import (
    PhantomPositionAuditor,
)

from domain.trading_state import (
    BrokerOrderState,
    CapitalReservationState,
    GridLevelState,
    InstrumentTradingState,
    OpenPositionState,
    TradingSessionState,
)

from infrastructure.sqlite.trading_state_repository import (
    TradingStateRepository,
)


def make_state(
    session_id: str = "sandbox:acct:abc",
    with_positions: bool = True,
    with_orders: bool = False,
    extra_active_instrument: bool = False,
) -> TradingSessionState:
    levels = [
        GridLevelState(
            level_index=0,
            level_price=Decimal(
                "100"
            ),
            status=(
                "POSITION_OPENED"
                if with_positions
                else "WAITING_PRICE"
            ),
        ),
    ]

    positions = (
        [
            OpenPositionState(
                level_index=0,
                entry_price=Decimal(
                    "100"
                ),
                quantity=3,
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

        if with_positions

        else []
    )

    orders = (
        [
            BrokerOrderState(
                broker_order_id=(
                    "order-1"
                ),
                request_id=None,
                instrument_uid=(
                    "uid-SBER"
                ),
                ticker="SBER",
                level_index=0,
                side="SELL",
                quantity=3,
                limit_price=Decimal(
                    "105"
                ),
                status="PLACED",
            )
        ]

        if with_orders

        else []
    )

    instruments = [
        InstrumentTradingState(
            ticker="SBER",
            instrument_uid=(
                "uid-SBER"
            ),
            current_price=Decimal(
                "100"
            ),
            realized_profit=Decimal(
                "0"
            ),
            levels=levels,
            open_positions=(
                positions
            ),
            active_orders=(
                orders
            ),
        )
    ]

    if extra_active_instrument:
        instruments.append(
            InstrumentTradingState(
                ticker="GAZP",
                instrument_uid=(
                    "uid-GAZP"
                ),
                current_price=None,
                realized_profit=Decimal(
                    "5"
                ),
                levels=[
                    GridLevelState(
                        level_index=0,
                        level_price=Decimal(
                            "200"
                        ),
                        status=(
                            "POSITION_OPENED"
                        ),
                    )
                ],
                open_positions=[
                    OpenPositionState(
                        level_index=0,
                        entry_price=Decimal(
                            "200"
                        ),
                        quantity=2,
                        buy_commission=Decimal(
                            "0.6"
                        ),
                        hard_take_profit_price=Decimal(
                            "210"
                        ),
                        expected_sell_commission_percent=(
                            Decimal(
                                "0.3"
                            )
                        ),
                    )
                ],
                active_orders=[],
            )
        )

    return TradingSessionState(
        schema_version=4,
        session_id=(
            session_id
        ),
        trading_account_id=(
            "tinvest:sbx-broker-1"
        ),
        broker_account_id=(
            "sbx-broker-1"
        ),
        mode="sandbox",
        status="STOPPED",
        available_cash=Decimal(
            "1000"
        ),
        reserved_cash=Decimal(
            "300"
        ),
        instruments=(
            instruments
        ),
        reservations=[
            CapitalReservationState(
                instrument_uid=(
                    "uid-SBER"
                ),
                level_index=0,
                amount=Decimal(
                    "300"
                ),
            )
        ],
    )


def test_audit_reports_phantom_when_broker_empty() -> None:
    auditor = (
        PhantomPositionAuditor()
    )

    report = (
        auditor
        .audit(
            snapshots=[
                make_state()
            ],

            broker_positions_by_account={
                "sbx-broker-1": {},
            },
        )
    )

    assert (
        len(
            report
            .phantoms
        )
        == 1
    )

    phantom = (
        report
        .phantoms[
            0
        ]
    )

    assert (
        phantom
        .ticker
        == "SBER"
    )

    assert (
        phantom
        .open_lots
        == 3
    )

    assert (
        phantom
        .broker_lots
        == 0
    )


def test_audit_skips_instrument_present_at_broker() -> None:
    auditor = (
        PhantomPositionAuditor()
    )

    report = (
        auditor
        .audit(
            snapshots=[
                make_state()
            ],

            broker_positions_by_account={
                "sbx-broker-1": {
                    "uid-SBER": 3,
                },
            },
        )
    )

    assert (
        report
        .phantoms
        == []
    )


def test_audit_skips_active_runner_snapshots() -> None:
    auditor = (
        PhantomPositionAuditor()
    )

    report = (
        auditor
        .audit(
            snapshots=[
                make_state()
            ],

            broker_positions_by_account={
                "sbx-broker-1": {},
            },

            active_session_ids={
                "sandbox:acct:abc"
            },
        )
    )

    assert (
        report
        .phantoms
        == []
    )


def test_audit_reports_phantom_orders_without_positions() -> None:
    auditor = (
        PhantomPositionAuditor()
    )

    report = (
        auditor
        .audit(
            snapshots=[
                make_state(
                    with_positions=(
                        False
                    ),

                    with_orders=(
                        True
                    ),
                )
            ],

            broker_positions_by_account={
                "sbx-broker-1": {},
            },
        )
    )

    assert (
        len(
            report
            .phantoms
        )
        == 1
    )

    assert (
        report
        .phantoms[
            0
        ]
        .active_orders
        == 1
    )


def test_clean_resets_instrument_and_keeps_snapshot() -> None:
    auditor = (
        PhantomPositionAuditor()
    )

    state = (
        make_state(
            extra_active_instrument=(
                True
            )
        )
    )

    #
    # У второго инструмента есть
    # реальная позиция — snapshot
    # должен сохраниться.
    #
    cleaned = (
        auditor
        .clean(
            state=state,

            instrument_uids={
                "uid-SBER"
            },
        )
    )

    assert (
        cleaned
        is state
    )

    sber = (
        state
        .instruments[
            0
        ]
    )

    assert (
        sber
        .open_positions
        == []
    )

    assert (
        sber
        .active_orders
        == []
    )

    assert (
        sber
        .levels[
            0
        ]
        .status
        == "WAITING_PRICE"
    )

    assert (
        state
        .reservations
        == []
    )


def test_clean_returns_none_when_nothing_remains() -> None:
    auditor = (
        PhantomPositionAuditor()
    )

    cleaned = (
        auditor
        .clean(
            state=(
                make_state()
            ),

            instrument_uids={
                "uid-SBER"
            },
        )
    )

    assert (
        cleaned
        is None
    )


def test_repository_get_all_returns_any_status(
    tmp_path: Path,
) -> None:
    db_path = (
        tmp_path
        / "state.db"
    )

    repository = (
        TradingStateRepository(
            db_path=str(
                db_path
            ),
        )
    )

    stopped = (
        make_state(
            session_id=(
                "sandbox:acct:stopped"
            )
        )
    )

    stopped.status = (
        "STOPPED"
    )

    running = (
        make_state(
            session_id=(
                "sandbox:acct:running"
            )
        )
    )

    running.status = (
        "RUNNING"
    )

    repository.save(
        stopped
    )

    repository.save(
        running
    )

    active = (
        repository
        .get_active()
    )

    assert [
        item
        .session_id

        for item
        in active
    ] == [
        "sandbox:acct:running"
    ]

    all_states = (
        repository
        .get_all()
    )

    assert {
        item
        .session_id

        for item
        in all_states
    } == {
        "sandbox:acct:stopped",

        "sandbox:acct:running",
    }
