from decimal import Decimal

from application.multi_instrument_session_config import (
    InstrumentConfig,
    MultiInstrumentSessionConfig,
)
from application.portfolio_orchestrator import PortfolioOrchestrator


def test_portfolio_start_plan_matches_business_logic() -> None:
    config = MultiInstrumentSessionConfig(
        instruments=[
            InstrumentConfig(
                ticker="SBER",
                levels_count=20,
                quantity=1,
            ),
        ]
    )

    plan = PortfolioOrchestrator().build_start_plan(
        config=config,
        price_ranges_by_ticker={
            "SBER": (
                Decimal("100"),
                Decimal("200"),
            ),
        },
        prices_by_ticker={
            "SBER": Decimal("200"),
        },
        available_cash=Decimal("1000"),
    )

    instrument = plan.instruments[0]
    levels = instrument.capital_plan.levels

    assert len(levels) == 20

    assert levels[0].price < Decimal("200")
    assert levels[-1].price <= Decimal("100")

    assert levels[0].step_percent_from_previous >= Decimal("0.15")
    assert levels[1].step_from_previous > levels[0].step_from_previous
    assert levels[2].step_from_previous > levels[1].step_from_previous

    actual_quantities = [
        level.quantity
        for level in levels
    ]

    assert actual_quantities == [
        1,
        1,
        1,
        1,
        1,
        1,
        2,
        1,
        1,
        2,
        1,
        2,
        1,
        2,
        2,
        2,
        1,
        2,
        2,
        2,
    ]

    assert instrument.required_deposit == instrument.capital_plan.total_amount
    assert plan.can_start is False
    assert plan.can_start_forced is True
    assert plan.missing_cash > Decimal("0")
    assert "Недостаточно капитала" in plan.warning_message
