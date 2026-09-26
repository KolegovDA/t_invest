from decimal import Decimal

from application.instrument_selector import (
    InstrumentCandidate,
    InstrumentSelector,
)
from strategy.confidence_score import (
    ConfidenceScore,
)
from strategy.risk_score import (
    HIGH_BAND,
    LOW_BAND,
    MEDIUM_BAND,
    RiskScore,
)


def candidate(
    ticker: str,
    confidence: str,
    band: str = LOW_BAND,
    risk_value: str = "10",
) -> (
    InstrumentCandidate
):
    return (
        InstrumentCandidate(
            ticker=ticker,

            instrument_uid=(
                f"uid_{ticker}"
            ),

            name=(
                f"Name {ticker}"
            ),

            risk_score=(
                RiskScore(
                    instrument_id=(
                        f"uid_{ticker}"
                    ),

                    value=Decimal(
                        risk_value
                    ),

                    band=band,

                    volatility_percent=(
                        Decimal("1")
                    ),

                    max_drawdown_percent=(
                        Decimal("10")
                    ),
                )
            ),

            confidence_score=(
                ConfidenceScore(
                    instrument_id=(
                        f"uid_{ticker}"
                    ),

                    value=Decimal(
                        confidence
                    ),

                    band="ACCEPTABLE",
                )
            ),
        )
    )


def test_selector_splits_capital_equally() -> None:
    plan = (
        InstrumentSelector()
        .build_plan(
            candidates=[
                candidate(
                    "SBER",
                    "80",
                ),

                candidate(
                    "GAZP",
                    "70",
                ),
            ],

            capital=Decimal(
                "100000"
            ),
        )
    )

    assert not plan.is_empty

    assert (
        len(plan.selections)
        == 2
    )

    assert (
        plan.selections[
            0
        ].ticker
        == "SBER"
    )

    total = sum(
        selection
        .allocated_capital

        for selection
        in plan.selections
    )

    assert (
        total
        == Decimal("100000")
    )

    for selection in (
        plan.selections
    ):
        assert (
            selection
            .weight_percent
            == Decimal("50.00")
        )


def test_selector_sorts_by_confidence_and_applies_limit() -> None:
    plan = (
        InstrumentSelector(
            max_instruments=2,
        )
        .build_plan(
            candidates=[
                candidate(
                    "A",
                    "55",
                ),

                candidate(
                    "B",
                    "90",
                ),

                candidate(
                    "C",
                    "70",
                ),
            ],

            capital=Decimal(
                "30000"
            ),
        )
    )

    assert [
        selection.ticker

        for selection
        in plan.selections
    ] == ["B", "C"]

    assert [
        rejected.ticker

        for rejected
        in plan.rejected
    ] == ["A"]


def test_selector_rejects_high_risk_and_low_confidence() -> None:
    plan = (
        InstrumentSelector()
        .build_plan(
            candidates=[
                candidate(
                    "RISKY",

                    "80",

                    band=HIGH_BAND,

                    risk_value="75",
                ),

                candidate(
                    "WEAK",

                    "20",
                ),
            ],

            capital=Decimal(
                "10000"
            ),
        )
    )

    assert plan.is_empty

    reasons = {
        rejected.ticker: (
            rejected.reason
        )

        for rejected
        in plan.rejected
    }

    assert (
        "высокий риск"
        in reasons["RISKY"]
    )

    assert (
        "confidence"
        in reasons["WEAK"]
    )


def test_selector_skips_duplicate_tickers() -> None:
    plan = (
        InstrumentSelector()
        .build_plan(
            candidates=[
                candidate(
                    "SBER",
                    "80",
                ),

                candidate(
                    "sber",
                    "60",
                ),
            ],

            capital=Decimal(
                "10000"
            ),
        )
    )

    assert (
        len(plan.selections)
        == 1
    )

    assert (
        len(plan.rejected)
        == 1
    )

    assert (
        plan.rejected[
            0
        ].reason
        == "дубликат"
    )


def test_selector_requires_positive_capital() -> None:
    try:
        InstrumentSelector().build_plan(
            candidates=[],

            capital=Decimal("0"),
        )

        assert False

    except ValueError:
        assert True
