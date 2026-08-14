from decimal import Decimal

from domain.trading_state import (
    BrokerOrderState,
    GridLevelState,
    InstrumentTradingState,
    OpenPositionState,
    TradingSessionState,
)
from infrastructure.sqlite.trading_state_repository import (
    TradingStateRepository,
)


def test_trading_state_repository_save_and_load(
    tmp_path,
) -> None:
    db_path = (
        tmp_path
        / "test.db"
    )

    repository = (
        TradingStateRepository(
            db_path=str(
                db_path
            )
        )
    )

    state = TradingSessionState(
        schema_version=1,

        session_id="session-1",

        trading_account_id=(
            "account-local-1"
        ),

        broker_account_id=(
            "2011718042"
        ),

        mode="live",
        status="RUNNING",

        available_cash=Decimal(
            "2945.60"
        ),

        reserved_cash=Decimal(
            "897.30"
        ),

        instruments=[
            InstrumentTradingState(
                ticker="SBER",

                instrument_uid=(
                    "SBER_UID"
                ),

                current_price=Decimal(
                    "281.10"
                ),

                realized_profit=Decimal(
                    "12.34"
                ),

                levels=[
                    GridLevelState(
                        level_index=1,
                        level_price=Decimal(
                            "280"
                        ),
                        status=(
                            "POSITION_OPENED"
                        ),
                    ),
                    GridLevelState(
                        level_index=2,
                        level_price=Decimal(
                            "275"
                        ),
                        status=(
                            "TRAILING_ENTRY"
                        ),
                        trailing_entry_lowest_price=Decimal(
                            "273.50"
                        ),
                        trailing_entry_confirmed=False,
                    ),
                ],

                open_positions=[
                    OpenPositionState(
                        level_index=1,

                        entry_price=Decimal(
                            "278.20"
                        ),

                        quantity=1,

                        buy_commission=Decimal(
                            "0.83"
                        ),

                        hard_take_profit_price=Decimal(
                            "281.30"
                        ),

                        expected_sell_commission_percent=Decimal(
                            "0.30"
                        ),

                        trailing_exit_target_price=Decimal(
                            "282.70"
                        ),

                        trailing_exit_highest_price=Decimal(
                            "283.40"
                        ),

                        trailing_exit_confirmed=False,
                    )
                ],

                active_orders=[
                    BrokerOrderState(
                        broker_order_id=(
                            "83082018478"
                        ),

                        request_id=(
                            "request-1"
                        ),

                        instrument_uid=(
                            "SBER_UID"
                        ),

                        ticker="SBER",

                        level_index=1,

                        side="SELL",

                        quantity=1,

                        limit_price=Decimal(
                            "282.90"
                        ),

                        status="NEW",

                        lots_requested=1,
                        lots_executed=0,

                        executed_price=None,
                    )
                ],
            )
        ],
    )

    repository.save(
        state
    )

    restored = repository.get(
        "session-1"
    )

    assert restored is not None

    assert (
        restored.session_id
        == state.session_id
    )

    assert (
        restored.broker_account_id
        == "2011718042"
    )

    assert (
        restored.available_cash
        == Decimal("2945.60")
    )

    assert (
        len(
            restored.instruments
        )
        == 1
    )

    instrument = (
        restored.instruments[0]
    )

    assert (
        instrument.ticker
        == "SBER"
    )

    assert (
        instrument.realized_profit
        == Decimal("12.34")
    )

    assert (
        len(
            instrument.levels
        )
        == 2
    )

    assert (
        instrument.levels[1]
        .trailing_entry_lowest_price
        == Decimal("273.50")
    )

    assert (
        len(
            instrument.open_positions
        )
        == 1
    )

    position = (
        instrument
        .open_positions[0]
    )

    assert (
        position.entry_price
        == Decimal("278.20")
    )

    assert (
        position
        .trailing_exit_highest_price
        == Decimal("283.40")
    )

    assert (
        len(
            instrument.active_orders
        )
        == 1
    )

    order = (
        instrument
        .active_orders[0]
    )

    assert (
        order.broker_order_id
        == "83082018478"
    )

    assert (
        order.limit_price
        == Decimal("282.90")
    )


def test_get_active_returns_only_active_states(
    tmp_path,
) -> None:
    repository = TradingStateRepository(
        db_path=str(
            tmp_path
            / "test.db"
        )
    )

    active = TradingSessionState(
        schema_version=1,
        session_id="active",
        trading_account_id="a1",
        broker_account_id="b1",
        mode="live",
        status="RUNNING",
        available_cash=Decimal("1000"),
        reserved_cash=Decimal("0"),
        instruments=[],
    )

    stopped = TradingSessionState(
        schema_version=1,
        session_id="stopped",
        trading_account_id="a1",
        broker_account_id="b1",
        mode="live",
        status="STOPPED",
        available_cash=Decimal("1000"),
        reserved_cash=Decimal("0"),
        instruments=[],
    )

    repository.save(active)
    repository.save(stopped)

    result = repository.get_active()

    assert len(result) == 1
    assert result[0].session_id == "active"


def test_save_updates_existing_snapshot(
    tmp_path,
) -> None:
    repository = TradingStateRepository(
        db_path=str(
            tmp_path
            / "test.db"
        )
    )

    state = TradingSessionState(
        schema_version=1,
        session_id="session",
        trading_account_id="a1",
        broker_account_id="b1",
        mode="live",
        status="RUNNING",
        available_cash=Decimal("1000"),
        reserved_cash=Decimal("0"),
        instruments=[],
    )

    repository.save(state)

    state.available_cash = Decimal(
        "900"
    )

    state.reserved_cash = Decimal(
        "100"
    )

    repository.save(state)

    restored = repository.get(
        "session"
    )

    assert restored is not None

    assert (
        restored.available_cash
        == Decimal("900")
    )

    assert (
        restored.reserved_cash
        == Decimal("100")
    )
