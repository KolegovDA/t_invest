from datetime import (
    datetime,
    timedelta,
    timezone,
)
from decimal import Decimal

from domain.commands import (
    PlaceSellAllLimitCommand,
)
from domain.events import (
    TradeExecutedEvent,
)
from domain.positions import (
    OpenLevelPosition,
)
from strategy.grid_engine import (
    GridEngine,
    GridEngineConfig,
    GridLevel,
)
from strategy.grid_risk_manager import (
    GridRiskManager,
    GridRiskManagerConfig,
)


def create_position(
    level_index: int,
    entry_price: Decimal = Decimal("100"),
) -> OpenLevelPosition:
    return OpenLevelPosition(
        level_index=level_index,
        entry_price=entry_price,
        quantity=1,
        buy_commission=Decimal("0"),
        expected_sell_commission_percent=(
            Decimal("0.30")
        ),
        hard_take_profit_price=(
            Decimal("101")
        ),
        purchase_cost=entry_price,
    )


def create_positions(
    count: int,
) -> dict[int, OpenLevelPosition]:
    return {
        index: create_position(
            level_index=index,
        )
        for index in range(
            1,
            count + 1,
        )
    }


def create_manager(
    min_working_time: int = 86400,
) -> GridRiskManager:
    return GridRiskManager(
        instrument_id="SBER",

        config=(
            GridRiskManagerConfig(
                min_open_positions_for_compensation=5,

                compensation_multiplier=(
                    Decimal("3")
                ),

                emergency_sell_offset_percent=(
                    Decimal("0.15")
                ),

                early_close_min_working_time_seconds=(
                    min_working_time
                ),

                early_close_profit_loss_ratio=(
                    Decimal("3")
                ),
            )
        ),
    )


def test_early_close_does_not_start_before_min_working_time() -> None:
    manager = create_manager()

    commands = (
        manager
        .check_early_close(
            open_positions=(
                create_positions(
                    count=2,
                )
            ),

            realized_profit=Decimal(
                "1000"
            ),

            current_price=Decimal(
                "99"
            ),

            grid_age_seconds=86399,
        )
    )

    assert (
        commands
        == []
    )

    assert (
        manager
        .compensation_order_pending
        is False
    )


def test_early_close_does_not_start_without_grid_age() -> None:
    manager = create_manager()

    commands = (
        manager
        .check_early_close(
            open_positions=(
                create_positions(
                    count=2,
                )
            ),

            realized_profit=Decimal(
                "1000"
            ),

            current_price=Decimal(
                "99"
            ),

            grid_age_seconds=None,
        )
    )

    assert (
        commands
        == []
    )


def test_early_close_is_disabled_when_min_working_time_is_zero() -> None:
    manager = (
        create_manager(
            min_working_time=0,
        )
    )

    commands = (
        manager
        .check_early_close(
            open_positions=(
                create_positions(
                    count=2,
                )
            ),

            realized_profit=Decimal(
                "1000"
            ),

            current_price=Decimal(
                "99"
            ),

            grid_age_seconds=(
                10_000_000
            ),
        )
    )

    assert (
        commands
        == []
    )


def test_early_close_does_not_start_without_positions() -> None:
    manager = create_manager()

    commands = (
        manager
        .check_early_close(
            open_positions={},

            realized_profit=Decimal(
                "1000"
            ),

            current_price=Decimal(
                "99"
            ),

            grid_age_seconds=(
                10_000_000
            ),
        )
    )

    assert (
        commands
        == []
    )


def test_early_close_does_not_start_without_floating_loss() -> None:
    manager = create_manager()

    commands = (
        manager
        .check_early_close(
            open_positions=(
                create_positions(
                    count=2,
                )
            ),

            realized_profit=Decimal(
                "1000"
            ),

            current_price=Decimal(
                "105"
            ),

            grid_age_seconds=(
                10_000_000
            ),
        )
    )

    assert (
        commands
        == []
    )


def test_early_close_does_not_start_when_profit_is_less_than_loss_times_ratio() -> None:
    manager = create_manager()

    #
    # floating loss = 2,
    # требуется 2 × 3 = 6.
    #
    commands = (
        manager
        .check_early_close(
            open_positions=(
                create_positions(
                    count=2,
                )
            ),

            realized_profit=Decimal(
                "5.99"
            ),

            current_price=Decimal(
                "99"
            ),

            grid_age_seconds=(
                10_000_000
            ),
        )
    )

    assert (
        commands
        == []
    )


def test_early_close_starts_with_two_positions_after_min_working_time() -> None:
    manager = create_manager()

    commands = (
        manager
        .check_early_close(
            open_positions=(
                create_positions(
                    count=2,
                )
            ),

            realized_profit=Decimal(
                "6"
            ),

            current_price=Decimal(
                "99"
            ),

            grid_age_seconds=(
                10_000_000
            ),
        )
    )

    assert (
        len(commands)
        == 1
    )

    command = commands[0]

    assert isinstance(
        command,

        PlaceSellAllLimitCommand,
    )

    assert (
        command.instrument_id
        == "SBER"
    )

    assert (
        command.quantity
        == 2
    )

    assert (
        command.price
        == (
            Decimal("99")
            * Decimal("0.9985")
        )
    )

    assert (
        command.reason
        == "EARLY_CLOSE_X3"
    )

    assert (
        manager
        .compensation_order_pending
        is True
    )


def test_early_close_does_not_send_second_order_while_first_is_pending() -> None:
    manager = create_manager()

    positions = (
        create_positions(
            count=2,
        )
    )

    first_commands = (
        manager
        .check_early_close(
            open_positions=(
                positions
            ),

            realized_profit=Decimal(
                "6"
            ),

            current_price=Decimal(
                "99"
            ),

            grid_age_seconds=(
                10_000_000
            ),
        )
    )

    assert (
        len(first_commands)
        == 1
    )

    second_commands = (
        manager
        .check_early_close(
            open_positions=(
                positions
            ),

            realized_profit=Decimal(
                "1000"
            ),

            current_price=Decimal(
                "99"
            ),

            grid_age_seconds=(
                10_000_000
            ),
        )
    )

    assert (
        second_commands
        == []
    )


def create_grid() -> GridEngine:
    return GridEngine(
        instrument_id="SBER",

        levels=[
            GridLevel(
                index=1,
                price=Decimal("100"),
            ),
            GridLevel(
                index=2,
                price=Decimal("99"),
            ),
        ],

        config=(
            GridEngineConfig(
                quantity=1,
            )
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
    level_index: int,
    price: Decimal,
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

            commission=(
                Decimal("0")
            ),

            total_amount=price,
        )
    )


def test_grid_engine_sets_grid_opened_at_on_first_buy() -> None:
    grid = create_grid()

    assert (
        grid.grid_opened_at
        is None
    )

    open_position(
        grid=grid,

        level_index=1,

        price=Decimal("100"),
    )

    assert (
        grid.grid_opened_at
        is not None
    )


def test_grid_engine_resets_grid_opened_at_after_full_close() -> None:
    grid = create_grid()

    open_position(
        grid=grid,

        level_index=1,

        price=Decimal("100"),
    )

    open_position(
        grid=grid,

        level_index=2,

        price=Decimal("99"),
    )

    grid.on_trade_executed(
        TradeExecutedEvent(
            instrument_id="SBER",

            level_index=1,

            side="SELL",

            quantity=1,

            price=Decimal("101"),

            commission=(
                Decimal("0")
            ),

            total_amount=(
                Decimal("101")
            ),
        )
    )

    assert (
        grid.grid_opened_at
        is not None
    )

    grid.on_trade_executed(
        TradeExecutedEvent(
            instrument_id="SBER",

            level_index=2,

            side="SELL",

            quantity=1,

            price=Decimal("101"),

            commission=(
                Decimal("0")
            ),

            total_amount=(
                Decimal("101")
            ),
        )
    )

    assert (
        grid.grid_opened_at
        is None
    )


def test_grid_engine_emits_early_close_after_min_working_time() -> None:
    grid = create_grid()

    open_position(
        grid=grid,

        level_index=1,

        price=Decimal("100"),
    )

    open_position(
        grid=grid,

        level_index=2,

        price=Decimal("99"),
    )

    grid.realized_profit = (
        Decimal("6")
    )

    #
    # Сетка в рынке уже больше
    # суток: 90000 секунд.
    #
    grid.grid_opened_at = (
        datetime.now(
            timezone.utc
        )
        - timedelta(
            seconds=90000,
        )
    )

    fresh_commands = (
        grid.on_price(
            Decimal("98.5")
        )
    )

    sell_all = [
        command
        for command
        in fresh_commands
        if isinstance(
            command,

            PlaceSellAllLimitCommand,
        )
    ]

    assert (
        len(sell_all)
        == 1
    )

    assert (
        sell_all[0]
        .reason
        == "EARLY_CLOSE_X3"
    )

    assert (
        sell_all[0]
        .quantity
        == 2
    )

    repeated_commands = (
        grid.on_price(
            Decimal("98.5")
        )
    )

    repeated_sell_all = [
        command
        for command
        in repeated_commands
        if isinstance(
            command,

            PlaceSellAllLimitCommand,
        )
    ]

    assert (
        repeated_sell_all
        == []
    )


def test_grid_engine_does_not_emit_early_close_when_grid_is_fresh() -> None:
    grid = create_grid()

    open_position(
        grid=grid,

        level_index=1,

        price=Decimal("100"),
    )

    open_position(
        grid=grid,

        level_index=2,

        price=Decimal("99"),
    )

    grid.realized_profit = (
        Decimal("1000")
    )

    commands = (
        grid.on_price(
            Decimal("98.5")
        )
    )

    sell_all = [
        command
        for command
        in commands
        if isinstance(
            command,

            PlaceSellAllLimitCommand,
        )
    ]

    assert (
        sell_all
        == []
    )
