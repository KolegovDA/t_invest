from decimal import Decimal

from application.multi_instrument_session_config import (
    InstrumentConfig,
    MultiInstrumentSessionConfig,
)
from application.portfolio_orchestrator import (
    PortfolioOrchestrator,
)


def test_portfolio_orchestrator_builds_start_plan() -> None:
    config = MultiInstrumentSessionConfig(
        sandbox_deposit=Decimal("100000"),
        instruments=[
            InstrumentConfig(
                ticker="SBER",
                levels_count=20,
                quantity=1,
            ),
            InstrumentConfig(
                ticker="GAZP",
                levels_count=20,
                quantity=1,
            ),
        ],
    )

    plan = PortfolioOrchestrator().build_start_plan(
        config=config,
        prices_by_ticker={
            "SBER": Decimal("300"),
            "GAZP": Decimal("160"),
        },
        available_cash=Decimal("100000"),
    )

    assert len(plan.instruments) == 2
    assert plan.total_required_deposit == Decimal("9227.600")
    assert plan.can_start is True


def test_portfolio_orchestrator_blocks_start_when_cash_is_not_enough() -> None:
    config = MultiInstrumentSessionConfig(
        sandbox_deposit=Decimal("100000"),
        instruments=[
            InstrumentConfig(
                ticker="SBER",
                levels_count=20,
                quantity=1,
            ),
            InstrumentConfig(
                ticker="GAZP",
                levels_count=20,
                quantity=1,
            ),
        ],
    )

    plan = PortfolioOrchestrator().build_start_plan(
        config=config,
        prices_by_ticker={
            "SBER": Decimal("300"),
            "GAZP": Decimal("160"),
        },
        available_cash=Decimal("1000"),
    )

    assert plan.can_start is False
