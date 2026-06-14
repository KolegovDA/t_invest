from decimal import Decimal

from backtest.backtest_report import BacktestReportBuilder
from backtest.backtest_scenario import SampleScenarioFactory
from backtest.backtester import Backtester
from strategy.grid_engine import GridEngineConfig


def main() -> None:
    scenario = SampleScenarioFactory().create_sber_compensation_scenario()

    backtester = Backtester(
        initial_cash=Decimal("100000"),
    )

    result = backtester.run(
        instrument_id=scenario.instrument_id,
        history_candles=scenario.history_candles,
        price_series=scenario.price_series,
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
