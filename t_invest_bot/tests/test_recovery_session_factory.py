from decimal import Decimal

from application.recovered_session_state import RecoveredSessionState
from application.recovery_session_factory import RecoverySessionFactory
from domain.portfolio import InstrumentPortfolio, Portfolio
from portfolio.capital_reservation_manager import CapitalReservationManager
from strategy.grid_engine import GridLevel, GridLevelStatus, OpenLevelPosition


def test_recovery_session_factory_restores_grid_engine() -> None:
    state = RecoveredSessionState(
        session_id="session-1",
        account_id="account-1",
        ticker="SBER",
        instrument_id="SBER_ID",
        status="ACTIVE",
        levels=[
            GridLevel(
                index=1,
                price=Decimal("300"),
                status=GridLevelStatus.POSITION_OPENED,
            ),
        ],
        positions={
            1: OpenLevelPosition(
                level_index=1,
                entry_price=Decimal("300"),
                quantity=10,
                buy_commission=Decimal("9"),
                expected_sell_commission_percent=Decimal("0.30"),
                hard_take_profit_price=Decimal("310"),
            ),
        },
        portfolio=Portfolio(
            cash=Decimal("100000"),
            instruments={
                "SBER_ID": InstrumentPortfolio(
                    instrument_id="SBER_ID",
                    position_quantity=10,
                    average_price=Decimal("300"),
                    realized_profit=Decimal("100"),
                    buy_commission_total=Decimal("9"),
                    last_price=Decimal("305"),
                )
            },
        ),
        reservation_manager=CapitalReservationManager(
            available_cash=Decimal("100000"),
        ),
    )

    grid_engine = RecoverySessionFactory().create_grid_engine(
        state=state,
    )

    assert grid_engine.instrument_id == "SBER_ID"
    assert len(grid_engine.levels) == 1
    assert grid_engine.levels[0].status == GridLevelStatus.POSITION_OPENED
    assert grid_engine.open_positions[1].entry_price == Decimal("300")
    assert grid_engine.open_positions[1].quantity == 10
    assert grid_engine.realized_profit == Decimal("100")
