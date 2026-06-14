from decimal import Decimal

from portfolio.portfolio_start_decision import PortfolioStartDecisionService


def test_start_decision_allows_start_when_cash_is_enough() -> None:
    decision = PortfolioStartDecisionService().decide(
        available_cash=Decimal("100000"),
        required_deposit=Decimal("60000"),
        allow_underfunded_start=False,
    )

    assert decision.can_start is True
    assert decision.is_underfunded is False
    assert decision.warning is None


def test_start_decision_blocks_when_cash_is_not_enough() -> None:
    decision = PortfolioStartDecisionService().decide(
        available_cash=Decimal("10000"),
        required_deposit=Decimal("60000"),
        allow_underfunded_start=False,
    )

    assert decision.can_start is False
    assert decision.is_underfunded is True
    assert decision.warning is not None


def test_start_decision_allows_underfunded_start_with_warning() -> None:
    decision = PortfolioStartDecisionService().decide(
        available_cash=Decimal("10000"),
        required_deposit=Decimal("60000"),
        allow_underfunded_start=True,
    )

    assert decision.can_start is True
    assert decision.is_underfunded is True
    assert decision.warning is not None
