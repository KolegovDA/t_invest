from decimal import Decimal

import pytest

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


@pytest.mark.parametrize("amount,count,expected", [
    ("6", 0, "0.06"),
    ("6", 1, "0.063"),
    ("6", 2, "0.0661"),
    ("6", 100, "0.18"),
    ("9", 0, "0.09"),
    ("12", 0, "0.12"),
])
def test_order_value_growth_uses_open_position_count_and_exchange_step(amount, count, expected):
    config = GridEngineConfig(base_order_amount=Decimal(amount), quantity_step=Decimal("0.0001"))
    quantity = config.buy_quantity(Decimal("100"), count)
    assert quantity == Decimal(expected)
    assert quantity * Decimal("100") <= Decimal(amount) * Decimal("3")


def test_fixed_integer_sizing_remains_unchanged_without_order_amount():
    config = GridEngineConfig(quantity=7)
    assert config.buy_quantity(Decimal("100"), 50) == 7
    assert isinstance(config.buy_quantity(Decimal("100"), 50), int)


@pytest.mark.parametrize("minimum_quantity,minimum_amount", [("0.061", "0"), ("0", "6.01")])
def test_order_sizing_does_not_increase_budget_to_meet_exchange_minimums(minimum_quantity, minimum_amount):
    config = GridEngineConfig(
        base_order_amount=Decimal("6"), quantity_step=Decimal("0.0001"),
        min_quantity=Decimal(minimum_quantity), min_order_amount=Decimal(minimum_amount),
    )
    assert config.buy_quantity(Decimal("100"), 0) == 0


@pytest.mark.parametrize("field,value", [
    ("base_order_amount", "NaN"), ("base_order_amount", "0"),
    ("quantity_step", "0"), ("quantity_step", "Infinity"),
    ("order_amount_multiplier", "0.9"), ("max_order_amount_multiplier", "0.9"),
    ("min_quantity", "-1"), ("min_order_amount", "NaN"),
])
def test_invalid_order_sizing_is_rejected(field, value):
    config = GridEngineConfig(base_order_amount=Decimal("6"))
    setattr(config, field, Decimal(value))
    with pytest.raises(ValueError):
        config.buy_quantity(Decimal("100"), 0)


def test_buy_command_uses_fractional_sizing_and_preserves_trailing_when_below_minimum():
    from domain.enums import GridLevelStatus

    grid = create_grid()
    grid.config.base_order_amount = Decimal("6")
    grid.config.quantity_step = Decimal("0.0001")
    grid.config.min_order_amount = Decimal("10")
    grid.config.fallback_buy_commission_percent = Decimal("0.1")
    grid.on_price(Decimal("100.5"))
    grid.on_price(Decimal("101"))
    trigger = grid.levels[0].trailing_entry.trigger_price
    assert grid.on_price(trigger) == []
    assert grid.levels[0].status == GridLevelStatus.TRAILING_ENTRY
    grid.config.min_order_amount = Decimal("5")
    command = grid.on_price(trigger)[0]
    assert isinstance(command, PlaceBuyLimitCommand)
    assert command.quantity == grid.config.buy_quantity(command.price, 0)
    assert command.quantity * command.price <= Decimal("6")
    assert command.commission_percent == Decimal("0.1")
    assert grid.on_price(trigger) == []


def test_fractional_partial_fills_keep_exact_quantity_and_cost():
    grid = create_grid()
    grid.on_trade_executed(TradeExecutedEvent("SBER", 1, "BUY", Decimal("0.03"), Decimal("100"), Decimal("0")))
    grid.on_trade_executed(TradeExecutedEvent("SBER", 1, "BUY", Decimal("0.03"), Decimal("100"), Decimal("0")))
    assert len(grid.open_positions) == 1
    grid.on_trade_executed(TradeExecutedEvent("SBER", 1, "SELL", Decimal("0.02"), Decimal("110"), Decimal("0")))
    assert grid.open_positions[1].quantity == Decimal("0.04")
    assert grid.open_positions[1].purchase_cost == Decimal("4")
    assert grid.realized_profit == Decimal("0.2")
    assert grid.completed_cycles == []


def test_partial_sell_keeps_unsold_position_and_does_not_close_grid():
    grid = create_grid()
    grid.on_trade_executed(TradeExecutedEvent("SBER", 1, "BUY", 2, Decimal("100"), Decimal("0")))
    grid.on_trade_executed(TradeExecutedEvent("SBER", 1, "SELL", 1, Decimal("110"), Decimal("0")))
    assert grid.open_positions[1].quantity == 1
    assert grid.open_positions[1].purchase_cost == Decimal("100")
    assert grid.realized_profit == Decimal("10")
    assert grid.completed_cycles == []
    grid.on_trade_executed(TradeExecutedEvent("SBER", 1, "SELL", 1, Decimal("110"), Decimal("0")))
    assert not grid.open_positions
    assert Decimal(grid.completed_cycles[0]["profit"]) == Decimal("20")


def test_all_future_levels_recalculate_immediately_after_buy_and_sell():
    grid = create_grid()
    grid.on_trade_executed(TradeExecutedEvent("SBER", 1, "BUY", 1, Decimal("100.37")))
    assert [level.price for level in grid.levels] == [Decimal("100.37"), Decimal("99.37"), Decimal("98.37"), Decimal("97.37")]
    grid.on_trade_executed(TradeExecutedEvent("SBER", 2, "BUY", 1, Decimal("99.22")))
    assert grid.levels[2].price == Decimal("98.22")
    assert grid.levels[3].price == Decimal("97.22")
    grid.on_trade_executed(TradeExecutedEvent("SBER", 2, "SELL", 1, Decimal("101")))
    assert grid.levels[1].price == Decimal("99.37")
    assert grid.levels[2].price == Decimal("98.37")


def test_recalculation_preserves_submitted_orders_and_active_trailing():
    from domain.enums import GridLevelStatus

    grid = create_grid()
    grid.levels[2].status = GridLevelStatus.ORDER_PLACED
    grid.levels[2].price = Decimal("95")
    grid.on_trade_executed(TradeExecutedEvent("SBER", 1, "BUY", 1, Decimal("100.37")))
    assert grid.levels[2].price == Decimal("95")
    assert grid.levels[2].status == GridLevelStatus.ORDER_PLACED


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
