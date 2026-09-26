from __future__ import annotations

from dataclasses import dataclass
from decimal import (
    Decimal,
    ROUND_HALF_UP,
)

from domain.instrument_statistics import (
    InstrumentStatistics,
)
from strategy.risk_score import (
    RiskScore,
)


WEAK_BAND = "WEAK"

ACCEPTABLE_BAND = (
    "ACCEPTABLE"
)

STRONG_BAND = "STRONG"


def _clamp(
    value: Decimal,
) -> Decimal:
    if value < Decimal("0"):
        return Decimal("0")

    if value > Decimal("100"):
        return Decimal("100")

    return value


@dataclass(slots=True)
class ConfidenceScore:
    instrument_id: str

    value: Decimal

    band: str


@dataclass(slots=True)
class ConfidenceScoreCalculator:
    """
    ConfidenceScore v1.1.

    Насколько бот «уверен»
    в инструменте:

    100 - RiskScore
    + бонус за подтверждённую
    историю циклов (win rate
    и средний плюс на цикл),
    максимум +15.

    Полосы:
      WEAK       < 40
      ACCEPTABLE < 70
      STRONG     >= 70
    """

    weak_band_threshold: (
        Decimal
    ) = Decimal("40")

    strong_band_threshold: (
        Decimal
    ) = Decimal("70")

    max_history_bonus: (
        Decimal
    ) = Decimal("15")

    def calculate(
        self,
        instrument_id: str,
        risk_score: RiskScore,
        statistics: (
            InstrumentStatistics
            | None
        ) = None,
    ) -> (
        ConfidenceScore
    ):
        value = (
            Decimal("100")
            - risk_score.value
        )

        value += (
            self
            ._history_bonus(
                statistics,
            )
        )

        value = _clamp(
            value,
        ).quantize(
            Decimal("0.01"),

            rounding=(
                ROUND_HALF_UP
            ),
        )

        return ConfidenceScore(
            instrument_id=(
                instrument_id
            ),

            value=value,

            band=self._band(
                value,
            ),
        )

    def _band(
        self,
        value: Decimal,
    ) -> str:
        if (
            value
            < self
            .weak_band_threshold
        ):
            return WEAK_BAND

        if (
            value
            < self
            .strong_band_threshold
        ):
            return ACCEPTABLE_BAND

        return STRONG_BAND

    def _history_bonus(
        self,
        statistics: (
            InstrumentStatistics
            | None
        ),
    ) -> Decimal:
        if (
            statistics
            is None
        ):
            return Decimal("0")

        if (
            statistics
            .total_cycles
            <= 0
        ):
            return Decimal("0")

        win_rate = (
            Decimal(
                statistics
                .profitable_cycles,
            )

            / Decimal(
                statistics
                .total_cycles,
            )
        )

        bonus = (
            win_rate
            * self
            .max_history_bonus
        )

        if (
            statistics
            .average_cycle_profit
            < Decimal("0")
        ):
            bonus /= Decimal("2")

        return bonus
