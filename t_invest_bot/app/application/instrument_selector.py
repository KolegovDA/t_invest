from __future__ import annotations

from dataclasses import (
    dataclass,
    field,
)
from decimal import (
    Decimal,
    ROUND_HALF_UP,
)

from strategy.confidence_score import (
    ConfidenceScore,
)
from strategy.risk_score import (
    HIGH_BAND,
    RiskScore,
)


@dataclass(slots=True)
class InstrumentCandidate:
    ticker: str

    instrument_uid: str

    name: str = ""

    risk_score: (
        RiskScore | None
    ) = None

    confidence_score: (
        ConfidenceScore
        | None
    ) = None


@dataclass(slots=True)
class InstrumentSelection:
    ticker: str

    instrument_uid: str

    name: str

    weight_percent: Decimal

    allocated_capital: Decimal

    confidence_value: (
        Decimal | None
    )

    risk_band: str | None


@dataclass(slots=True)
class RejectedInstrument:
    ticker: str

    reason: str


@dataclass(slots=True)
class InstrumentSelectionPlan:
    capital: Decimal

    selections: list[
        InstrumentSelection
    ] = field(
        default_factory=list,
    )

    rejected: list[
        RejectedInstrument
    ] = field(
        default_factory=list,
    )

    @property
    def is_empty(
        self,
    ) -> bool:
        return not (
            self.selections
        )


@dataclass(slots=True)
class InstrumentSelector:
    """
    Индексный режим v1.1.

    Из кандидатов отбираются
    лучшие по ConfidenceScore
    (без HIGH-риска), капитал
    делится равными долями —
    как в индексном фонде.
    """

    max_instruments: int = 5

    min_confidence: (
        Decimal
    ) = Decimal("40")

    allow_high_risk: bool = False

    def build_plan(
        self,
        candidates: list[
            InstrumentCandidate
        ],
        capital: Decimal,
    ) -> (
        InstrumentSelectionPlan
    ):
        if capital <= Decimal("0"):
            raise ValueError(
                "Capital must be "
                "greater than zero"
            )

        plan = (
            InstrumentSelectionPlan(
                capital=capital,
            )
        )

        accepted = []

        seen_tickers: set[
            str
        ] = set()

        for candidate in (
            candidates
        ):
            ticker = (
                candidate
                .ticker
                .upper()
            )

            if (
                ticker
                in seen_tickers
            ):
                plan.rejected.append(
                    RejectedInstrument(
                        ticker=ticker,

                        reason=(
                            "дубликат"
                        ),
                    )
                )

                continue

            seen_tickers.add(
                ticker,
            )

            reason = (
                self
                ._rejection_reason(
                    candidate,
                )
            )

            if reason:
                plan.rejected.append(
                    RejectedInstrument(
                        ticker=ticker,

                        reason=reason,
                    )
                )

                continue

            accepted.append(
                candidate,
            )

        accepted.sort(
            key=lambda candidate: (
                candidate
                .confidence_score
                .value
            ),

            reverse=True,
        )

        selected = accepted[
            : self
            .max_instruments
        ]

        for candidate in (
            accepted[
                self
                .max_instruments:
            ]
        ):
            plan.rejected.append(
                RejectedInstrument(
                    ticker=(
                        candidate
                        .ticker
                        .upper()
                    ),

                    reason=(
                        "лимит "
                        f"{self.max_instruments} "
                        "инструментов"
                    ),
                )
            )

        if not selected:
            return plan

        count = Decimal(
            len(selected),
        )

        allocated = (
            (
                capital
                / count
            ).quantize(
                Decimal("0.01"),

                rounding=(
                    ROUND_HALF_UP
                ),
            )
        )

        weight = (
            (
                Decimal("100")
                / count
            ).quantize(
                Decimal("0.01"),

                rounding=(
                    ROUND_HALF_UP
                ),
            )
        )

        allocated_total = (
            Decimal("0")
        )

        for index, (
            candidate
        ) in enumerate(
            selected,
        ):
            #
            # Остаток от деления
            # отдаём первому —
            # сумма должна сойтись
            # в капитал.
            #
            candidate_allocated = (
                allocated
            )

            if index == 0:
                candidate_allocated = (
                    capital
                    - allocated
                    * (
                        count - 1
                    )
                ).quantize(
                    Decimal("0.01"),

                    rounding=(
                        ROUND_HALF_UP
                    ),
                )

            allocated_total += (
                candidate_allocated
            )

            plan.selections.append(
                InstrumentSelection(
                    ticker=(
                        candidate
                        .ticker
                        .upper()
                    ),

                    instrument_uid=(
                        candidate
                        .instrument_uid
                    ),

                    name=(
                        candidate
                        .name
                    ),

                    weight_percent=(
                        weight
                    ),

                    allocated_capital=(
                        candidate_allocated
                    ),

                    confidence_value=(
                        candidate
                        .confidence_score
                        .value
                    ),

                    risk_band=(
                        candidate
                        .risk_score
                        .band
                    ),
                )
            )

        return plan

    def _rejection_reason(
        self,
        candidate: (
            InstrumentCandidate
        ),
    ) -> str | None:
        if (
            candidate
            .confidence_score
            is None
        ):
            return (
                "нет ConfidenceScore"
            )

        if (
            candidate
            .risk_score
            is None
        ):
            return (
                "нет RiskScore"
            )

        if (
            not self
            .allow_high_risk

            and candidate
            .risk_score.band
            == HIGH_BAND
        ):
            return (
                "высокий риск "
                f"({candidate.risk_score.value})"
            )

        if (
            candidate
            .confidence_score.value
            < self
            .min_confidence
        ):
            return (
                "confidence "
                f"{candidate.confidence_score.value} "
                f"< {self.min_confidence}"
            )

        return None
