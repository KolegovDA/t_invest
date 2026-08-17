from backtest.backtest_config import (
    BacktestConfig,
)
from backtest.backtest_report import (
    BacktestReportBuilder,
)
from backtest.backtest_runner import (
    BacktestRunner,
)
from backtest.backtest_scenario import (
    SampleScenarioFactory,
)


def test_sber_scenario_is_profitable_with_new_entry_logic(
) -> None:
    scenario = (
        SampleScenarioFactory()
        .create_sber_compensation_scenario()
    )

    config = BacktestConfig(
        initial_cash=100000,
        levels_count=5,
        quantity=10,
    )

    runner = BacktestRunner(
        report_builder=(
            BacktestReportBuilder()
        ),
    )

    result = runner.run(
        scenario=scenario,
        config=config,
    )

    #
    # После перехода на новую
    # динамическую BUY-механику
    # этот исторический сценарий
    # больше не является
    # гарантированным сценарием
    # компенсационного закрытия.
    #
    # Поэтому здесь проверяем,
    # что стратегия:
    #
    # - реально совершает сделки;
    # - закрывает сделки в плюс;
    # - не генерирует убыточных
    #   закрытых сделок;
    # - корректно оставляет
    #   незавершённые позиции
    #   открытыми.
    #
    assert (
        result.report.total_trades
        > 0
    )

    assert (
        result.report.buy_trades
        > 0
    )

    assert (
        result.report.sell_trades
        > 0
    )

    assert (
        result.report.net_profit
        > 0
    )

    assert (
        result.report.winning_trades
        > 0
    )

    assert (
        result.report.losing_trades
        == 0
    )

    assert (
        result.report.final_cash
        > 0
    )

    #
    # В текущем сценарии после
    # новой BUY-логики остаются
    # позиции, которые ещё не
    # достигли условий своего
    # индивидуального выхода.
    #
    # Это не ошибка компенсации:
    # одновременно открыто меньше
    # 5 уровней.
    #
    assert (
        result.report
        .open_positions_count
        < config
        .min_open_positions_for_compensation
    )


def test_sber_scenario_trade_counts_are_consistent(
) -> None:
    scenario = (
        SampleScenarioFactory()
        .create_sber_compensation_scenario()
    )

    config = BacktestConfig(
        initial_cash=100000,
        levels_count=5,
        quantity=10,
    )

    runner = BacktestRunner(
        report_builder=(
            BacktestReportBuilder()
        ),
    )

    result = runner.run(
        scenario=scenario,
        config=config,
    )

    #
    # Каждая сделка в отчёте
    # должна быть либо BUY,
    # либо SELL.
    #
    assert (
        result.report
        .total_trades
        ==
        (
            result.report
            .buy_trades
            +
            result.report
            .sell_trades
        )
    )

    #
    # Закрытых прибыльных +
    # убыточных сделок не может
    # быть больше количества SELL.
    #
    assert (
        (
            result.report
            .winning_trades
            +
            result.report
            .losing_trades
        )
        <= result.report
        .sell_trades
    )

    #
    # Количество оставшихся
    # позиций не может быть
    # отрицательным и не должно
    # превышать размер сетки.
    #
    assert (
        0
        <= result.report
        .open_positions_count
        <= config.levels_count
    )
