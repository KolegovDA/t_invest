from __future__ import annotations

from dataclasses import dataclass
from decimal import (
    Decimal,
    ROUND_HALF_UP,
)

from domain.entities import Candle


LOW_BAND = "LOW"

MEDIUM_BAND = "MEDIUM"

HIGH_BAND = "HIGH"


def _clamp(
    value: Decimal,
) -> Decimal:
    if value < Decimal("0"):
        return Decimal("0")

    if value > Decimal("100"):
        return Decimal("100")

    return value


@dataclass(slots=True)
class RiskScore:
    instrument_id: str

    value: Decimal

    band: str

    volatility_percent: (
        Decimal
    )

    max_drawdown_percent: (
        Decimal
    )


@dataclass(slots=True)
class RiskScoreCalculator:
    """
    RiskScore v1.1.

    Оценка риска инструмента по
    дневной истории:
    - волатильность (сигма
      доходностей закрытия);
    - максимальная просадка.

    Итог 0..100:
      0.5 * min(100, сигма% * 20)
      + 0.5 * min(100, просадка% * 1.5)

    Полосы:
      LOW    < 30
      MEDIUM < 60
      HIGH   >= 60
    """

    low_band_threshold: (
        Decimal
    ) = Decimal("30")

    high_band_threshold: (
        Decimal
    ) = Decimal("60")

    def calculate(
        self,
        instrument_id: str,
        candles: list[
            Candle
        ],
    ) -> RiskScore:
        if len(candles) < 2:
            raise ValueError(
                "At least two candles "
                "are required for "
                "risk score"
            )

        sorted_candles = sorted(
            candles,
            key=lambda candle: (
                candle.timestamp
            ),
        )

        volatility = (
            self
            ._volatility_percent(
                sorted_candles,
            )
        )

        drawdown = (
            self
            ._max_drawdown_percent(
                sorted_candles,
            )
        )

        volatility_part = (
            _clamp(
                volatility
                * Decimal("20"),
            )
        )

        drawdown_part = (
            _clamp(
                drawdown
                * Decimal("1.5"),
            )
        )

        value = _clamp(
            volatility_part
            / Decimal("2")

            + drawdown_part
            / Decimal("2"),
        ).quantize(
            Decimal("0.01"),

            rounding=(
                ROUND_HALF_UP
            ),
        )

        return RiskScore(
            instrument_id=(
                instrument_id
            ),

            value=value,

            band=self._band(
                value,
            ),

            volatility_percent=(
                volatility
                .quantize(
                    Decimal(
                        "0.01"
                    ),

                    rounding=(
                        ROUND_HALF_UP
                    ),
                )
            ),

            max_drawdown_percent=(
                drawdown
                .quantize(
                    Decimal(
                        "0.01"
                    ),

                    rounding=(
                        ROUND_HALF_UP
                    ),
                )
            ),
        )

    def _band(
        self,
        value: Decimal,
    ) -> str:
        if (
            value
            < self
            .low_band_threshold
        ):
            return LOW_BAND

        if (
            value
            < self
            .high_band_threshold
        ):
            return MEDIUM_BAND

        return HIGH_BAND

    @staticmethod
    def _volatility_percent(
        candles: list[Candle],
    ) -> Decimal:
        returns: list[
            Decimal
        ] = []

        for index in range(
            1,
            len(candles),
        ):
            previous_close = (
                candles[
                    index - 1
                ]
                .close
            )

            close = (
                candles[
                    index
                ]
                .close
            )

            if (
                previous_close
                <= Decimal("0")
            ):
                raise ValueError(
                    "Candle close must "
                    "be greater than "
                    "zero"
                )

            returns.append(
                (
                    (
                        close
                        - previous_close
                    )

                    / previous_close

                    * Decimal("100")
                )
            )

        count = Decimal(
            len(returns),
        )

        mean = (
            sum(returns)
            / count
        )

        variance = (
            sum(
                (
                    single_return
                    - mean
                )
                ** 2

                for single_return
                in returns
            )

            / count
        )

        return variance.sqrt()

    @staticmethod
    def _max_drawdown_percent(
        candles: list[Candle],
    ) -> Decimal:
        peak = (
            candles[0].close
        )

        max_drawdown = (
            Decimal("0")
        )

        for candle in candles:
            if (
                candle.close
                > peak
            ):
                peak = (
                    candle
                    .close
                )

                continue

            if (
                peak
                <= Decimal("0")
            ):
                raise ValueError(
                    "Candle close must "
                    "be greater than "
                    "zero"
                )

            drawdown = (
                (
                    (
                        peak
                        - candle.close
                    )

                    / peak

                    * Decimal("100")
                )
            )

            if (
                drawdown
                > max_drawdown
            ):
                max_drawdown = (
                    drawdown
                )

        return max_drawdown
