from datetime import (
    datetime,
    timedelta,
)
from decimal import Decimal

from domain.entities import Candle
from strategy.confidence_score import (
    ConfidenceScoreCalculator,
)
from strategy.risk_score import (
    HIGH_BAND,
    LOW_BAND,
    MEDIUM_BAND,
    RiskScore,
    RiskScoreCalculator,
)


def make_candles(
    closes: list[str],
    start: str = "2026-06-01",
) -> list[Candle]:
    first = datetime.fromisoformat(
        start,
    )

    return [
        Candle(
            instrument_id="TEST",

            open=Decimal(close),
            high=Decimal(close),
            low=Decimal(close),
            close=Decimal(close),

            volume=1000,

            timestamp=(
                first
                + timedelta(
                    days=index,
                )
            ),
        )

        for index, close
        in enumerate(closes)
    ]


def test_risk_score_requires_two_candles() -> None:
    calculator = (
        RiskScoreCalculator()
    )

    try:
        calculator.calculate(
            instrument_id="TEST",

            candles=make_candles(
                ["100"],
            ),
        )

        assert False

    except ValueError:
        assert True


def test_risk_score_flat_series_is_low() -> None:
    score = (
        RiskScoreCalculator()
        .calculate(
            instrument_id="TEST",

            candles=make_candles(
                [
                    "100",
                    "100.5",
                    "100",
                    "100.5",
                    "100",
                    "100.5",
                    "100",
                ]
            ),
        )
    )

    assert (
        score.band
        == LOW_BAND
    )

    assert (
        score.value
        < Decimal("30")
    )

    assert (
        score.max_drawdown_percent
        < Decimal("1")
    )


def test_risk_score_crash_series_is_high() -> None:
    score = (
        RiskScoreCalculator()
        .calculate(
            instrument_id="TEST",

            candles=make_candles(
                [
                    "100",
                    "102",
                    "101",
                    "103",
                    "80",
                    "70",
                    "65",
                    "66",
                    "60",
                ]
            ),
        )
    )

    assert (
        score.band
        == HIGH_BAND
    )

    assert (
        score.value
        >= Decimal("60")
    )

    assert (
        score.max_drawdown_percent
        >= Decimal("40")
    )


def test_risk_score_moderate_series_is_medium() -> None:
    score = (
        RiskScoreCalculator()
        .calculate(
            instrument_id="TEST",

            candles=make_candles(
                [
                    "100",
                    "101",
                    "99",
                    "100.5",
                    "98.5",
                    "100",
                    "99",
                    "100.5",
                    "99.5",
                ]
            ),
        )
    )

    assert (
        score.band
        in {
            LOW_BAND,
            MEDIUM_BAND,
        }
    )

    assert (
        Decimal("0")
        <= score.value
        <= Decimal("100")
    )


def test_confidence_score_inverse_to_risk() -> None:
    risk = RiskScore(
        instrument_id="TEST",

        value=Decimal("40"),

        band=MEDIUM_BAND,

        volatility_percent=(
            Decimal("2")
        ),

        max_drawdown_percent=(
            Decimal("25")
        ),
    )

    confidence = (
        ConfidenceScoreCalculator()
        .calculate(
            instrument_id="TEST",

            risk_score=risk,
        )
    )

    assert (
        confidence.value
        == Decimal("60.00")
    )

    assert (
        confidence.band
        == "ACCEPTABLE"
    )


def test_confidence_score_history_bonus() -> None:
    from domain.instrument_statistics import (
        InstrumentStatistics,
    )

    risk = RiskScore(
        instrument_id="TEST",

        value=Decimal("50"),

        band=MEDIUM_BAND,

        volatility_percent=(
            Decimal("2.5")
        ),

        max_drawdown_percent=(
            Decimal("33")
        ),
    )

    statistics = (
        InstrumentStatistics(
            instrument_id="TEST",

            total_cycles=10,

            profitable_cycles=8,

            losing_cycles=2,

            average_cycle_profit=(
                Decimal("5")
            ),
        )
    )

    confidence = (
        ConfidenceScoreCalculator()
        .calculate(
            instrument_id="TEST",

            risk_score=risk,

            statistics=(
                statistics
            ),
        )
    )

    #
    # 50 + 0.8 * 15 = 62
    #
    assert (
        confidence.value
        == Decimal("62.00")
    )


def test_confidence_score_strong_band() -> None:
    risk = RiskScore(
        instrument_id="TEST",

        value=Decimal("10"),

        band=LOW_BAND,

        volatility_percent=(
            Decimal("0.5")
        ),

        max_drawdown_percent=(
            Decimal("6")
        ),
    )

    confidence = (
        ConfidenceScoreCalculator()
        .calculate(
            instrument_id="TEST",

            risk_score=risk,
        )
    )

    assert (
        confidence.value
        == Decimal("90.00")
    )

    assert (
        confidence.band
        == "STRONG"
    )
