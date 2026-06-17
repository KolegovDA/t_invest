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
        ]
    )

    plan = PortfolioOrchestrator().build_start_plan(
        config=config,
        price_ranges_by_ticker={
            "SBER": (
                Decimal("200"),
                Decimal("350"),
            ),
            "GAZP": (
                Decimal("100"),
                Decimal("180"),
            ),
        },
        prices_by_ticker={
            "SBER": Decimal("300"),
            "GAZP": Decimal("160"),
        },
        available_cash=Decimal("100000"),
    )

    assert len(plan.instruments) == 2
    assert plan.total_required_deposit > Decimal("0")
    assert plan.can_start is True


def test_portfolio_orchestrator_blocks_start_when_cash_is_not_enough() -> None:
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
                Decimal("200"),
                Decimal("350"),
            ),
        },
        prices_by_ticker={
            "SBER": Decimal("300"),
        },
        available_cash=Decimal("100"),
    )

    assert plan.can_start is False
