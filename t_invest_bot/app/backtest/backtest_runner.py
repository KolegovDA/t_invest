from dataclasses import dataclass

from backtest.backtest_config import BacktestConfig
from backtest.backtest_report import BacktestReport, BacktestReportBuilder
from backtest.backtest_scenario import BacktestScenario
from backtest.backtester import Backtester, BacktestResult


@dataclass(slots=True)
class BacktestRunResult:
    backtest_result: BacktestResult
    report: BacktestReport


@dataclass(slots=True)
class BacktestRunner:
    report_builder: BacktestReportBuilder

    def run(
        self,
        scenario: BacktestScenario,
        config: BacktestConfig,
    ) -> BacktestRunResult:
        backtester = Backtester(
            initial_cash=config.initial_cash,
        )

        backtest_result = backtester.run(
            instrument_id=scenario.instrument_id,
            history_candles=scenario.history_candles,
            price_series=scenario.price_series,
            levels_count=config.levels_count,
            config=config.to_grid_engine_config(),
        )

        report = self.report_builder.build(
            result=backtest_result,
        )

        return BacktestRunResult(
            backtest_result=backtest_result,
            report=report,
        )
