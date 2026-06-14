from dataclasses import dataclass
from decimal import Decimal

from backtest.backtester import BacktestResult


@dataclass(slots=True)
class BacktestReport:
    instrument_id: str

    total_trades: int
    buy_trades: int
    sell_trades: int

    winning_trades: int
    losing_trades: int
    win_rate_percent: Decimal

    gross_profit: Decimal
    gross_loss: Decimal
    net_profit: Decimal
    profit_factor: Decimal
    return_percent: Decimal

    initial_cash: Decimal
    final_cash: Decimal

    open_positions_count: int

    max_drawdown: Decimal
    max_drawdown_percent: Decimal

    def print(self) -> None:
        print("----- BACKTEST REPORT -----")
        print(f"Instrument: {self.instrument_id}")
        print(f"Initial cash: {self.initial_cash}")
        print(f"Final cash: {self.final_cash}")
        print(f"Net profit: {self.net_profit}")
        print(f"Return: {self.return_percent}%")
        print(f"Profit factor: {self.profit_factor}")
        print(f"Win rate: {self.win_rate_percent}%")
        print(f"Winning trades: {self.winning_trades}")
        print(f"Losing trades: {self.losing_trades}")
        print(f"Max drawdown: {self.max_drawdown}")
        print(f"Max drawdown percent: {self.max_drawdown_percent}%")
        print(f"Total trades: {self.total_trades}")
        print(f"Buy trades: {self.buy_trades}")
        print(f"Sell trades: {self.sell_trades}")
        print(f"Gross profit: {self.gross_profit}")
        print(f"Gross loss: {self.gross_loss}")
        print(f"Open positions: {self.open_positions_count}")


class BacktestReportBuilder:
    def build(self, result: BacktestResult) -> BacktestReport:
        buy_trades = [
            trade
            for trade in result.trades
            if trade.side == "BUY"
        ]

        sell_trades = [
            trade
            for trade in result.trades
            if trade.side == "SELL"
        ]

        winning_trades = [
            trade
            for trade in sell_trades
            if trade.profit > Decimal("0")
        ]

        losing_trades = [
            trade
            for trade in sell_trades
            if trade.profit < Decimal("0")
        ]

        gross_profit = sum(
            (trade.profit for trade in winning_trades),
            Decimal("0"),
        )

        gross_loss = sum(
            (trade.profit for trade in losing_trades),
            Decimal("0"),
        )

        if gross_loss == Decimal("0"):
            profit_factor = Decimal("0")
        else:
            profit_factor = gross_profit / abs(gross_loss)

        if sell_trades:
            win_rate_percent = (
                Decimal(len(winning_trades))
                / Decimal(len(sell_trades))
                * Decimal("100")
            )
        else:
            win_rate_percent = Decimal("0")

        if result.initial_cash == Decimal("0"):
            return_percent = Decimal("0")
        else:
            return_percent = (
                result.realized_profit
                / result.initial_cash
                * Decimal("100")
            )

        return BacktestReport(
            instrument_id=result.instrument_id,
            total_trades=len(result.trades),
            buy_trades=len(buy_trades),
            sell_trades=len(sell_trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            win_rate_percent=win_rate_percent,
            gross_profit=gross_profit,
            gross_loss=gross_loss,
            net_profit=result.realized_profit,
            profit_factor=profit_factor,
            return_percent=return_percent,
            initial_cash=result.initial_cash,
            final_cash=result.final_cash,
            open_positions_count=result.open_positions_count,
            max_drawdown=result.max_drawdown,
            max_drawdown_percent=result.max_drawdown_percent,
        )
