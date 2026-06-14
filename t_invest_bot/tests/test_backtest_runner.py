from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "app"

sys.path.insert(0, str(APP_DIR))

from backtest.backtest_config import BacktestConfig
from backtest.backtest_report import BacktestReportBuilder
from backtest.backtest_runner import BacktestRunner
from backtest.backtest_scenario import SampleScenarioFactory


def test_sber_compensation_scenario_is_profitable_and_closes_positions() -> None:
    scenario = SampleScenarioFactory().create_sber_compensation_scenario()

    config = BacktestConfig(
        initial_cash=100000,
        levels_count=5,
        quantity=10,
    )

    runner = BacktestRunner(
        report_builder=BacktestReportBuilder(),
    )

    result = runner.run(
        scenario=scenario,
        config=config,
    )

    assert result.report.net_profit > 0
    assert result.report.open_positions_count == 0
    assert result.report.total_trades == 18
    assert result.report.sell_trades == 9
