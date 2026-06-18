from decimal import Decimal

from application.multi_instrument_session_config import (
    InstrumentConfig,
    MultiInstrumentSessionConfig,
)
from application.portfolio_capital_plan import CapitalPlan
from application.portfolio_orchestrator import (
    InstrumentCapitalPlan,
    PortfolioOrchestrator,
    PortfolioStartPlan,
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
    assert len(plan.instruments[0].capital_plan.levels) == 20


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


def test_portfolio_orchestrator_capital_plan_has_required_deposit() -> None:
    config = MultiInstrumentSessionConfig(
        instruments=[
            InstrumentConfig(
                ticker="SBER",
                levels_count=10,
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
        available_cash=Decimal("100000"),
    )

    instrument_plan = plan.instruments[0]

    assert instrument_plan.required_deposit == (
        instrument_plan.capital_plan.total_amount
    )
    assert instrument_plan.capital_plan.gross_amount > Decimal("0")
    assert instrument_plan.capital_plan.commission_amount > Decimal("0")


def test_portfolio_start_plan_calculates_remaining_cash_and_utilization() -> None:
    plan = PortfolioStartPlan(
        available_cash=Decimal("100000"),
        instruments=[
            InstrumentCapitalPlan(
                ticker="SBER",
                levels_count=20,
                quantity=1,
                last_price=Decimal("300"),
                required_deposit=Decimal("25000"),
                capital_plan=CapitalPlan(),
                historical_min_price=Decimal("200"),
                historical_max_price=Decimal("350"),
            ),
            InstrumentCapitalPlan(
                ticker="GAZP",
                levels_count=20,
                quantity=1,
                last_price=Decimal("100"),
                required_deposit=Decimal("15000"),
                capital_plan=CapitalPlan(),
                historical_min_price=Decimal("80"),
                historical_max_price=Decimal("180"),
            ),
        ],
    )

    assert plan.total_required_deposit == Decimal("40000")
    assert plan.remaining_cash == Decimal("60000")
    assert plan.missing_cash == Decimal("0")
    assert plan.capital_utilization_percent == Decimal("40.0")
    assert plan.can_start is True
    assert plan.can_start_forced is True
    assert plan.warning_message == ""


def test_portfolio_start_plan_warns_when_cash_is_not_enough() -> None:
    plan = PortfolioStartPlan(
        available_cash=Decimal("100000"),
        instruments=[
            InstrumentCapitalPlan(
                ticker="LKOH",
                levels_count=20,
                quantity=1,
                last_price=Decimal("4500"),
                required_deposit=Decimal("120000"),
                capital_plan=CapitalPlan(),
                historical_min_price=Decimal("3000"),
                historical_max_price=Decimal("6000"),
            ),
        ],
    )

    assert plan.can_start is False
    assert plan.can_start_forced is True
    assert plan.remaining_cash == Decimal("-20000")
    assert plan.missing_cash == Decimal("20000")
    assert "Недостаточно капитала" in plan.warning_message


def test_instrument_capital_plan_exposes_diagnostics() -> None:
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
        available_cash=Decimal("100000"),
    )

    instrument = plan.instruments[0]

    assert instrument.historical_min_price == Decimal("200")
    assert instrument.historical_max_price == Decimal("350")
    assert instrument.price_range_percent == Decimal("-33.33333333333333333333333333")
    assert instrument.max_level_quantity >= 1
    assert instrument.max_position_quantity >= instrument.max_level_quantity
