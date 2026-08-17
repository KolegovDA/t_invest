from decimal import Decimal

from domain.positions import (
    OpenLevelPosition,
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
            )
        ),
    )


def test_compensation_does_not_start_with_less_than_five_positions(
) -> None:
    manager = create_manager()

    positions = create_positions(
        count=4,
    )

    commands = (
        manager
        .check_compensation_close(
            open_positions=positions,

            realized_profit=Decimal(
                "1000"
            ),

            current_price=Decimal(
                "99"
            ),
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


def test_compensation_does_not_start_when_profit_is_less_than_loss_times_three(
) -> None:
    manager = create_manager()

    positions = create_positions(
        count=5,
    )

    #
    # Каждая позиция:
    #
    # BUY = 100
    # current = 99
    # loss = 1
    #
    # 5 позиций:
    # floating loss = 5
    #
    # Требуемая прибыль:
    # 5 × 3 = 15
    #
    commands = (
        manager
        .check_compensation_close(
            open_positions=positions,

            realized_profit=Decimal(
                "14.99"
            ),

            current_price=Decimal(
                "99"
            ),
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


def test_compensation_starts_exactly_at_loss_times_three(
) -> None:
    manager = create_manager()

    positions = create_positions(
        count=5,
    )

    commands = (
        manager
        .check_compensation_close(
            open_positions=positions,

            realized_profit=Decimal(
                "15"
            ),

            current_price=Decimal(
                "99"
            ),
        )
    )

    assert (
        len(commands)
        == 1
    )

    command = commands[0]

    assert (
        command.instrument_id
        == "SBER"
    )

    #
    # Закрываем все 5 позиций.
    #
    assert (
        command.quantity
        == 5
    )

    #
    # Компенсационный SELL:
    # 0.15% ниже рынка.
    #
    assert (
        command.price
        == (
            Decimal("99")
            * Decimal("0.9985")
        )
    )

    assert (
        command.reason
        == "COMPENSATION_CLOSE"
    )

    assert (
        manager
        .compensation_order_pending
        is True
    )


def test_compensation_does_not_send_second_order_while_first_is_pending(
) -> None:
    manager = create_manager()

    positions = create_positions(
        count=5,
    )

    first_commands = (
        manager
        .check_compensation_close(
            open_positions=positions,

            realized_profit=Decimal(
                "15"
            ),

            current_price=Decimal(
                "99"
            ),
        )
    )

    assert (
        len(first_commands)
        == 1
    )

    second_commands = (
        manager
        .check_compensation_close(
            open_positions=positions,

            realized_profit=Decimal(
                "1000"
            ),

            current_price=Decimal(
                "99"
            ),
        )
    )

    assert (
        second_commands
        == []
    )


def test_compensation_can_be_enabled_again_after_reset(
) -> None:
    manager = create_manager()

    positions = create_positions(
        count=5,
    )

    manager.check_compensation_close(
        open_positions=positions,

        realized_profit=Decimal(
            "15"
        ),

        current_price=Decimal(
            "99"
        ),
    )

    assert (
        manager
        .compensation_order_pending
        is True
    )

    manager.reset_compensation_order()

    assert (
        manager
        .compensation_order_pending
        is False
    )

    commands = (
        manager
        .check_compensation_close(
            open_positions=positions,

            realized_profit=Decimal(
                "15"
            ),

            current_price=Decimal(
                "99"
            ),
        )
    )

    assert (
        len(commands)
        == 1
    )
