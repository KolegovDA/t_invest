from decimal import Decimal

from domain.commands import (
    PlaceBuyLimitCommand,
)
from domain.events import (
    TradeExecutedEvent,
)
from strategy.grid_engine import (
    GridEngine,
    GridEngineConfig,
    GridLevel,
)


def create_grid() -> GridEngine:
    return GridEngine(
        instrument_id="SBER",

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

            GridLevel(
                index=4,
                price=Decimal("96"),
            ),
        ],

        config=(
            GridEngineConfig(
                quantity=1,

                first_entry_activation_percent=(
                    Decimal("0.50")
                ),

                entry_rebound_percent=(
                    Decimal("0.15")
                ),

                entry_limit_offset_percent=(
                    Decimal("0.15")
                ),
            )
        ),

        session_start_price=(
            Decimal("100")
        ),

        grid_step=(
            Decimal("1")
        ),
    )


def test_first_entry_does_not_activate_before_half_percent(
) -> None:
    grid = create_grid()

    assert (
        grid.on_price(
            Decimal("100.49")
        )
        == []
    )

    assert (
        grid.levels[0]
        .trailing_entry
        is None
    )


def test_first_entry_activates_after_positive_half_percent(
) -> None:
    grid = create_grid()

    assert (
        grid.on_price(
            Decimal("100.50")
        )
        == []
    )

    state = (
        grid.levels[0]
        .trailing_entry
    )

    assert state is not None

    assert (
        state.highest_price
        == Decimal("100.50")
    )

    expected_trigger = (
        Decimal("100.50")
        * Decimal("0.9985")
    )

    assert (
        state.trigger_price
        == expected_trigger
    )


def test_first_entry_activates_after_negative_half_percent(
) -> None:
    grid = create_grid()

    assert (
        grid.on_price(
            Decimal("99.50")
        )
        == []
    )

    state = (
        grid.levels[0]
        .trailing_entry
    )

    assert state is not None

    assert (
        state.highest_price
        == Decimal("99.50")
    )


def test_buy_trailing_moves_after_any_new_high(
) -> None:
    grid = create_grid()

    grid.on_price(
        Decimal("100.50")
    )

    state = (
        grid.levels[0]
        .trailing_entry
    )

    assert state is not None

    grid.on_price(
        Decimal("100.51")
    )

    assert (
        state.highest_price
        == Decimal("100.51")
    )

    assert (
        state.trigger_price
        == (
            Decimal("100.51")
            * Decimal("0.9985")
        )
    )

    grid.on_price(
        Decimal("100.511")
    )

    assert (
        state.highest_price
        == Decimal("100.511")
    )


def test_buy_trailing_never_moves_down(
) -> None:
    grid = create_grid()

    grid.on_price(
        Decimal("100.50")
    )

    grid.on_price(
        Decimal("101")
    )

    state = (
        grid.levels[0]
        .trailing_entry
    )

    assert state is not None

    trigger = (
        state.trigger_price
    )

    grid.on_price(
        Decimal("100.95")
    )

    assert (
        state.highest_price
        == Decimal("101")
    )

    assert (
        state.trigger_price
        == trigger
    )


def test_touching_buy_trailing_places_limit_above_market(
) -> None:
    grid = create_grid()

    grid.on_price(
        Decimal("100.50")
    )

    grid.on_price(
        Decimal("101")
    )

    state = (
        grid.levels[0]
        .trailing_entry
    )

    assert state is not None

    trigger_price = (
        state.trigger_price
    )

    assert (
        trigger_price
        is not None
    )

    commands = (
        grid.on_price(
            trigger_price
        )
    )

    assert len(commands) == 1

    command = commands[0]

    assert isinstance(
        command,
        PlaceBuyLimitCommand,
    )

    assert (
        command.level_index
        == 1
    )

    assert (
        command.price
        > trigger_price
    )

    assert (
        command.price
        == (
            trigger_price
            * Decimal("1.0015")
        )
    )


def test_second_level_is_calculated_from_real_first_buy_price(
) -> None:
    grid = create_grid()

    grid.on_trade_executed(
        TradeExecutedEvent(
            instrument_id="SBER",

            level_index=1,

            side="BUY",

            quantity=1,

            price=Decimal(
                "100.37"
            ),

            commission=Decimal(
                "0.30"
            ),
        )
    )

    #
    # Следующая точка:
    #
    # 100.37 - 1 = 99.37
    #
    assert (
        grid.on_price(
            Decimal("99.38")
        )
        == []
    )

    assert (
        grid.levels[1]
        .trailing_entry
        is None
    )

    assert (
        grid.on_price(
            Decimal("99.37")
        )
        == []
    )

    assert (
        grid.levels[1]
        .price
        == Decimal("99.37")
    )

    assert (
        grid.levels[1]
        .trailing_entry
        is not None
    )


def test_third_level_is_calculated_from_real_second_buy_price(
) -> None:
    grid = create_grid()

    grid.on_trade_executed(
        TradeExecutedEvent(
            instrument_id="SBER",
            level_index=1,
            side="BUY",
            quantity=1,
            price=Decimal("100.37"),
        )
    )

    grid.on_trade_executed(
        TradeExecutedEvent(
            instrument_id="SBER",
            level_index=2,
            side="BUY",
            quantity=1,
            price=Decimal("99.22"),
        )
    )

    #
    # Следующая точка №3:
    #
    # 99.22 - 1 = 98.22
    #
    grid.on_price(
        Decimal("98.22")
    )

    assert (
        grid.levels[2]
        .price
        == Decimal("98.22")
    )

    assert (
        grid.levels[2]
        .trailing_entry
        is not None
    )


def test_closed_third_level_can_be_used_again_from_second_level(
) -> None:
    grid = create_grid()

    grid.on_trade_executed(
        TradeExecutedEvent(
            instrument_id="SBER",
            level_index=1,
            side="BUY",
            quantity=1,
            price=Decimal("100"),
        )
    )

    grid.on_trade_executed(
        TradeExecutedEvent(
            instrument_id="SBER",
            level_index=2,
            side="BUY",
            quantity=1,
            price=Decimal("99"),
        )
    )

    grid.on_trade_executed(
        TradeExecutedEvent(
            instrument_id="SBER",
            level_index=3,
            side="BUY",
            quantity=1,
            price=Decimal("98"),
        )
    )

    #
    # №3 закрылся в прибыль.
    #
    grid.on_trade_executed(
        TradeExecutedEvent(
            instrument_id="SBER",
            level_index=3,
            side="SELL",
            quantity=1,
            price=Decimal("99"),
        )
    )

    assert (
        3
        not in grid.open_positions
    )

    assert (
        2
        in grid.open_positions
    )

    #
    # Новый №3 опять:
    #
    # BUY №2 = 99
    # step = 1
    #
    # activation = 98
    #
    grid.on_price(
        Decimal("98")
    )

    assert (
        grid.levels[2]
        .price
        == Decimal("98")
    )

    assert (
        grid.levels[2]
        .trailing_entry
        is not None
    )


def test_sell_order_does_not_block_next_buy_entry(
) -> None:
    grid = create_grid()

    grid.on_trade_executed(
        TradeExecutedEvent(
            instrument_id="SBER",
            level_index=1,
            side="BUY",
            quantity=1,
            price=Decimal("100"),
        )
    )

    #
    # Имитируем SELL order
    # по первому уровню.
    #
    level_1 = (
        grid.levels[0]
    )

    level_1.status = (
        type(level_1.status)
        .ORDER_PLACED
    )

    level_1.trailing_entry = None

    #
    # При этом BUY №2 всё равно
    # должен иметь право стартовать.
    #
    grid.on_price(
        Decimal("99")
    )

    assert (
        grid.levels[1]
        .trailing_entry
        is not None
    )
