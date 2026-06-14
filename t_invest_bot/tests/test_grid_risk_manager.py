from decimal import Decimal

from domain.commands import PlaceSellAllLimitCommand
from domain.positions import OpenLevelPosition
from strategy.grid_risk_manager import GridRiskManager, GridRiskManagerConfig


def test_grid_risk_manager_creates_single_sell_all_command() -> None:
    risk_manager = GridRiskManager(
        instrument_id="SBER",
        config=GridRiskManagerConfig(
            min_open_positions_for_compensation=5,
            compensation_multiplier=Decimal("3"),
            emergency_sell_offset_percent=Decimal("0.15"),
        ),
    )

    open_positions = {
        index: OpenLevelPosition(
            level_index=index,
            entry_price=Decimal("300"),
            quantity=10,
            buy_commission=Decimal("9"),
            expected_sell_commission_percent=Decimal("0.30"),
            hard_take_profit_price=Decimal("303"),
        )
        for index in range(1, 6)
    }

    current_price = Decimal("290")

    floating_loss = risk_manager.calculate_floating_loss(
        open_positions=open_positions,
        current_price=current_price,
    )

    commands = risk_manager.check_compensation_close(
        open_positions=open_positions,
        realized_profit=floating_loss * Decimal("3"),
        current_price=current_price,
    )

    assert len(commands) == 1
    assert isinstance(commands[0], PlaceSellAllLimitCommand)
    assert commands[0].instrument_id == "SBER"
    assert commands[0].quantity == 50
    assert commands[0].price == Decimal("289.5650")
