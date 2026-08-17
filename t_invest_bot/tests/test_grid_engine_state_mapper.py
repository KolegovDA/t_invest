from decimal import Decimal

from application.grid_engine_state_mapper import (
    GridEngineStateMapper,
)
from domain.events import (
    TradeExecutedEvent,
)
from strategy.grid_engine import (
    GridEngine,
    GridEngineConfig,
    GridLevel,
)


def create_engine() -> GridEngine:
    return GridEngine(
        instrument_id="SBER_UID",
        levels=[
            GridLevel(
                index=1,
                price=Decimal("300"),
            ),
            GridLevel(
                index=2,
                price=Decimal("290"),
            ),
            GridLevel(
                index=3,
                price=Decimal("280"),
            ),
        ],
        config=GridEngineConfig(
            quantity=1,
            trailing_percent=Decimal("0.50"),
            min_profit_percent=Decimal("0.30"),
            take_profit_buffer_percent=Decimal(
                "0.15"
            ),
            fallback_buy_commission_percent=Decimal(
                "0.30"
            ),
            fallback_sell_commission_percent=Decimal(
                "0.30"
            ),
        ),
    )


def test_grid_engine_state_can_be_restored() -> None:
    engine = create_engine()

    engine.on_trade_executed(
        TradeExecutedEvent(
            instrument_id="SBER_UID",
            level_index=1,
            side="BUY",
            quantity=1,
            price=Decimal("300"),
        )
    )

    position = (
        engine.open_positions[1]
    )

    activation_price = (
        engine
        ._calculate_exit_activation_price(
            position
            .hard_take_profit_price
        )
    )

    engine.on_price(
        activation_price
    )

    higher_price = (
        activation_price
        * Decimal("1.01")
    )

    engine.on_price(
        higher_price
    )

    assert (
        position.trailing_exit
        is not None
    )

    saved_highest_price = (
        position
        .trailing_exit
        .highest_price
    )

    mapper = (
        GridEngineStateMapper()
    )

    state = mapper.to_state(
        ticker="SBER",
        engine=engine,
        current_price=higher_price,
    )

    restored_engine = (
        create_engine()
    )

    mapper.restore(
        engine=restored_engine,
        state=state,
    )

    assert (
        restored_engine.realized_profit
        == engine.realized_profit
    )

    assert (
        len(
            restored_engine
            .open_positions
        )
        == 1
    )

    restored_position = (
        restored_engine
        .open_positions[1]
    )

    assert (
        restored_position.entry_price
        == Decimal("300")
    )

    assert (
        restored_position.quantity
        == 1
    )

    assert (
        restored_position
        .trailing_exit
        is not None
    )

    assert (
        restored_position
        .trailing_exit
        .highest_price
        == saved_highest_price
    )


def test_entry_trailing_survives_restart() -> None:
    engine = GridEngine(
        instrument_id="SBER_UID",

        levels=[
            GridLevel(
                index=1,
                price=Decimal("99"),
            ),
            GridLevel(
                index=2,
                price=Decimal("98"),
            ),
            GridLevel(
                index=3,
                price=Decimal("97"),
            ),
        ],

        config=GridEngineConfig(
            quantity=1,

            first_entry_activation_percent=(
                Decimal("0.50")
            ),

            entry_rebound_percent=(
                Decimal("0.15")
            ),
        ),

        session_start_price=(
            Decimal("100")
        ),

        grid_step=(
            Decimal("1")
        ),
    )

    engine.on_price(
        Decimal("100.50")
    )

    level = engine.levels[0]

    assert (
        level.trailing_entry
        is not None
    )

    engine.on_price(
        Decimal("101")
    )

    assert (
        level
        .trailing_entry
        .highest_price
        == Decimal("101")
    )

    mapper = (
        GridEngineStateMapper()
    )

    state = mapper.to_state(
        ticker="SBER",
        engine=engine,
        current_price=(
            Decimal("101")
        ),
    )

    restored_engine = GridEngine(
        instrument_id="SBER_UID",

        levels=[
            GridLevel(
                index=1,
                price=Decimal("99"),
            ),
            GridLevel(
                index=2,
                price=Decimal("98"),
            ),
            GridLevel(
                index=3,
                price=Decimal("97"),
            ),
        ],

        config=GridEngineConfig(
            quantity=1,

            first_entry_activation_percent=(
                Decimal("0.50")
            ),

            entry_rebound_percent=(
                Decimal("0.15")
            ),
        ),

        session_start_price=(
            Decimal("100")
        ),

        grid_step=(
            Decimal("1")
        ),
    )

    mapper.restore(
        engine=restored_engine,
        state=state,
    )

    restored_level = (
        restored_engine.levels[0]
    )

    assert (
        restored_level
        .trailing_entry
        is not None
    )

    #
    # Пока mapper сохраняет новое
    # значение через legacy
    # lowest_price.
    #
    assert (
        restored_level
        .trailing_entry
        .highest_price
        == Decimal("101")
    )


def test_realized_profit_survives_restart() -> None:
    engine = create_engine()

    engine.realized_profit = Decimal(
        "123.45"
    )

    mapper = (
        GridEngineStateMapper()
    )

    state = mapper.to_state(
        ticker="SBER",
        engine=engine,
    )

    restored_engine = (
        create_engine()
    )

    mapper.restore(
        engine=restored_engine,
        state=state,
    )

    assert (
        restored_engine
        .realized_profit
        == Decimal("123.45")
    )
