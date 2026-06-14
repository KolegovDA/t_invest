from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from domain.entities import Candle


@dataclass(slots=True)
class BacktestScenario:
    instrument_id: str
    history_candles: list[Candle]
    price_series: list[Decimal]


class SampleScenarioFactory:
    def create_sber_compensation_scenario(self) -> BacktestScenario:
        instrument_id = "SBER"

        history_candles = self._build_test_history(
            instrument_id=instrument_id,
        )

        price_series = [
            Decimal("305"),
            Decimal("300"),
            Decimal("296"),
            Decimal("292"),
            Decimal("288"),
            Decimal("284"),
            Decimal("280"),
            Decimal("280.50"),
            Decimal("286"),
            Decimal("292"),
            Decimal("298"),
            Decimal("304"),
            Decimal("302"),
            Decimal("300"),
            Decimal("296"),
            Decimal("292"),
            Decimal("288"),
            Decimal("284"),
            Decimal("280"),
            Decimal("280.50"),
            Decimal("286"),
            Decimal("292"),
            Decimal("298"),
            Decimal("304"),
            Decimal("302"),
            Decimal("300"),
            Decimal("296"),
            Decimal("292"),
            Decimal("288"),
            Decimal("284"),
            Decimal("280"),
            Decimal("276"),
            Decimal("272"),
            Decimal("268"),
            Decimal("264"),
            Decimal("260"),
            Decimal("260.50"),
            Decimal("259"),
            Decimal("259.50"),
            Decimal("258"),
            Decimal("258.50"),
            Decimal("257"),
            Decimal("257.50"),
            Decimal("256"),
            Decimal("256.50"),
            Decimal("256.20"),
        ]

        return BacktestScenario(
            instrument_id=instrument_id,
            history_candles=history_candles,
            price_series=price_series,
        )

    def _build_test_history(
        self,
        instrument_id: str,
    ) -> list[Candle]:
        history_start = datetime(2024, 1, 1)

        candles: list[Candle] = []

        for i in range(20):
            candles.append(
                Candle(
                    instrument_id=instrument_id,
                    open=Decimal("290"),
                    high=Decimal("310"),
                    low=Decimal("280"),
                    close=Decimal("290"),
                    volume=1000,
                    timestamp=history_start + timedelta(days=i),
                )
            )

        return candles
