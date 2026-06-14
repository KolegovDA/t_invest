from datetime import datetime, timedelta
from decimal import Decimal

from backtest.backtester import Backtester
from backtest.backtest_report import BacktestReportBuilder
from domain.entities import Candle
from strategy.grid_engine import GridEngineConfig


def build_test_history(instrument_id: str) -> list[Candle]:
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


def main() -> None:
    instrument_id = "SBER"

    history_candles = build_test_history(
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

    backtester = Backtester(
        initial_cash=Decimal("100000"),
    )

    result = backtester.run(
        instrument_id=instrument_id,
        history_candles=history_candles,
        price_series=price_series,
        levels_count=5,
        config=GridEngineConfig(
            quantity=10,
            min_open_positions_for_compensation=5,
            compensation_multiplier=Decimal("3"),
        ),
    )

    report = BacktestReportBuilder().build(result)
    report.print()


if __name__ == "__main__":
    main()
