from decimal import Decimal

from domain.commands import (
    PlaceBuyLimitCommand,
    PlaceSellLimitCommand,
)
from domain.events import (
    TradeExecutedEvent,
)
from strategy.grid_engine import (
    GridEngine,
    GridEngineConfig,
    GridLevel,
)


def create_grid(
) -> GridEngine:
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
        ],

        config=GridEngineConfig(
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

            trailing_percent=(
                Decimal("0.15")
            ),

            exit_limit_offset_percent=(
                Decimal("0.15")
            ),

            min_profit_percent=(
                Decimal("0.15")
            ),

            fallback_buy_commission_percent=(
                Decimal("0.30")
            ),

            fallback_sell_commission_percent=(
                Decimal("0.30")
            ),
        ),

        session_start_price=(
            Decimal("100")
        ),

        grid_step=(
            Decimal("1")
        ),
    )


def open_position(
    grid: GridEngine,

    level_index: int = 1,

    price: Decimal = Decimal("100"),

    commission: Decimal = Decimal("3"),

    total_amount: Decimal = Decimal(
        "1000"
    ),
) -> None:
    grid.on_trade_executed(
        TradeExecutedEvent(
            instrument_id="SBER",

            level_index=(
                level_index
            ),

            side="BUY",

            quantity=1,

            price=price,

            commission=commission,

            total_amount=(
                total_amount
            ),
        )
    )


def test_actual_buy_commission_is_used(
) -> None:
    grid = create_grid()

    open_position(
        grid=grid,
    )

    position = (
        grid.open_positions[1]
    )

    assert (
        position.buy_commission
        == Decimal("3")
    )

    assert (
        position.purchase_cost
        == Decimal("1003")
    )


def test_hard_take_profit_guarantees_point_15_percent_net_profit(
) -> None:
    grid = create_grid()

    open_position(
        grid=grid,
    )

    position = (
        grid.open_positions[1]
    )

    #
    # BUY:
    # gross = 1000
    # commission = 3
    #
    # purchase_cost = 1003
    #
    purchase_cost = Decimal(
        "1003"
    )

    minimum_profit = (
        purchase_cost
        * Decimal("0.0015")
    )

    required_net_sell = (
        purchase_cost
        + minimum_profit
    )

    expected_sell_rate = Decimal(
        "0.003"
    )

    required_gross_sell = (
        required_net_sell
        / (
            Decimal("1")
            - expected_sell_rate
        )
    )

    #
    # effective units:
    #
    # 1000 / 100 = 10
    #
    expected_price = (
        required_gross_sell
        / Decimal("10")
    )

    assert (
        position
        .hard_take_profit_price
        == expected_price
    )


def test_exit_activation_reserves_trailing_and_limit_offsets(
) -> None:
    grid = create_grid()

    open_position(
        grid=grid,
    )

    position = (
        grid.open_positions[1]
    )

    activation_price = (
        grid
        ._calculate_exit_activation_price(
            position
            .hard_take_profit_price
        )
    )

    #
    # Максимум достиг activation.
    #
    # Затем -0.15% trailing,
    # затем SELL limit ещё -0.15%.
    #
    after_trailing = (
        activation_price
        * Decimal("0.9985")
    )

    final_limit_price = (
        after_trailing
        * Decimal("0.9985")
    )

    assert (
        final_limit_price
        == position
        .hard_take_profit_price
    )


def test_trailing_exit_starts_but_does_not_sell_immediately(
) -> None:
    grid = create_grid()

    open_position(
        grid=grid,
    )

    position = (
        grid.open_positions[1]
    )

    activation_price = (
        grid
        ._calculate_exit_activation_price(
            position
            .hard_take_profit_price
        )
    )

    commands = grid.on_price(
        activation_price
    )

    assert (
        commands
        == []
    )

    assert (
        position.trailing_exit
        is not None
    )

    assert (
        position
        .trailing_exit
        .highest_price
        == activation_price
    )


def test_sell_trailing_moves_after_every_new_high(
) -> None:
    grid = create_grid()

    open_position(
        grid=grid,
    )

    position = (
        grid.open_positions[1]
    )

    activation_price = (
        grid
        ._calculate_exit_activation_price(
            position
            .hard_take_profit_price
        )
    )

    grid.on_price(
        activation_price
    )

    higher_price = (
        activation_price
        * Decimal("1.01")
    )

    assert (
        grid.on_price(
            higher_price
        )
        == []
    )

    assert (
        position
        .trailing_exit
        is not None
    )

    assert (
        position
        .trailing_exit
        .highest_price
        == higher_price
    )


def test_sell_limit_is_point_15_percent_below_market_after_trailing_touch(
) -> None:
    grid = create_grid()

    open_position(
        grid=grid,
    )

    position = (
        grid.open_positions[1]
    )

    activation_price = (
        grid
        ._calculate_exit_activation_price(
            position
            .hard_take_profit_price
        )
    )

    #
    # Дадим цене дополнительный
    # рост, чтобы SELL limit был
    # явно выше hard TP.
    #
    maximum_price = (
        activation_price
        * Decimal("1.01")
    )

    grid.on_price(
        maximum_price
    )

    rollback_price = (
        maximum_price
        * Decimal("0.9985")
    )

    commands = (
        grid.on_price(
            rollback_price
        )
    )

    assert (
        len(commands)
        == 1
    )

    command = commands[0]

    assert isinstance(
        command,
        PlaceSellLimitCommand,
    )

    expected_limit = (
        rollback_price
        * Decimal("0.9985")
    )

    assert (
        command.price
        == expected_limit
    )

    assert (
        command.price
        < rollback_price
    )

    assert (
        command.price
        >= position
        .hard_take_profit_price
    )


def test_sell_limit_never_goes_below_minimum_profitable_price(
) -> None:
    grid = create_grid()

    open_position(
        grid=grid,
    )

    position = (
        grid.open_positions[1]
    )

    activation_price = (
        grid
        ._calculate_exit_activation_price(
            position
            .hard_take_profit_price
        )
    )

    grid.on_price(
        activation_price
    )

    rollback_price = (
        activation_price
        * Decimal("0.9985")
    )

    commands = (
        grid.on_price(
            rollback_price
        )
    )

    assert (
        len(commands)
        == 1
    )

    assert (
        commands[0].price
        >= position
        .hard_take_profit_price
    )


def test_actual_sell_commission_is_used_for_realized_profit(
) -> None:
    grid = create_grid()

    open_position(
        grid=grid,
    )

    #
    # Фактическая продажа:
    #
    # gross = 1010
    # sell commission = 2.50
    #
    grid.on_trade_executed(
        TradeExecutedEvent(
            instrument_id="SBER",

            level_index=1,

            side="SELL",

            quantity=1,

            price=Decimal("101"),

            commission=Decimal(
                "2.50"
            ),

            total_amount=Decimal(
                "1010"
            ),
        )
    )

    #
    # purchase cost = 1003
    #
    # net sell = 1007.50
    #
    # profit = 4.50
    #
    assert (
        grid.realized_profit
        == Decimal("4.50")
    )

    assert (
        grid.total_sell_commission
        == Decimal("2.50")
    )

    assert (
        grid.open_positions
        == {}
    )


def test_each_position_has_independent_sell_target(
) -> None:
    grid = create_grid()

    open_position(
        grid=grid,

        level_index=1,

        price=Decimal("100"),

        commission=Decimal("3"),

        total_amount=Decimal(
            "1000"
        ),
    )

    open_position(
        grid=grid,

        level_index=2,

        price=Decimal("90"),

        commission=Decimal(
            "2.70"
        ),

        total_amount=Decimal(
            "900"
        ),
    )

    first = (
        grid.open_positions[1]
    )

    second = (
        grid.open_positions[2]
    )

    assert (
        first.entry_price
        == Decimal("100")
    )

    assert (
        second.entry_price
        == Decimal("90")
    )

    assert (
        first.hard_take_profit_price
        != second.hard_take_profit_price
    )


def test_buy_limit_is_above_current_price_after_entry_trailing(
) -> None:
    grid = create_grid()

    assert (
        grid.on_price(
            Decimal("100.49")
        )
        == []
    )

    assert (
        grid.on_price(
            Decimal("100.50")
        )
        == []
    )

    assert (
        grid.on_price(
            Decimal("101")
        )
        == []
    )

    state = (
        grid.levels[0]
        .trailing_entry
    )

    assert (
        state
        is not None
    )

    trailing_price = (
        state.trigger_price
    )

    assert (
        trailing_price
        is not None
    )

    commands = (
        grid.on_price(
            trailing_price
        )
    )

    assert (
        len(commands)
        == 1
    )

    command = (
        commands[0]
    )

    assert isinstance(
        command,
        PlaceBuyLimitCommand,
    )

    assert (
        command.price
        == (
            trailing_price
            * Decimal("1.0015")
        )
    )

    assert (
        command.price
        > trailing_price
    )
