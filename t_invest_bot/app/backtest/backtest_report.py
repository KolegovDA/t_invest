from dataclasses import dataclass
from decimal import Decimal

from backtest.backtester import BacktestResult


@dataclass(slots=True)
class BacktestReport:
    instrument_id: str

    total_trades: int
    buy_trades: int
    sell_trades: int

    gross_profit: Decimal
    gross_loss: Decimal
    net_profit: Decimal
    return_percent: Decimal

    initial_cash: Decimal
    final_cash: Decimal

    open_positions_count: int

    def print(self) -> None:
        print("----- BACKTEST REPORT -----")
        print(f"Instrument: {self.instrument_id}")
        print(f"Initial cash: {self.initial_cash}")
        print(f"Final cash: {self.final_cash}")
        print(f"Net profit: {self.net_profit}")
        print(f"Return: {self.return_percent}%")
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

        gross_profit = sum(
            (
                trade.profit
                for trade in sell_trades
                if trade.profit > Decimal("0")
            ),
            Decimal("0"),
        )

        gross_loss = sum(
            (
                trade.profit
                for trade in sell_trades
                if trade.profit < Decimal("0")
            ),
            Decimal("0"),
        )

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
            gross_profit=gross_profit,
            gross_loss=gross_loss,
            net_profit=result.realized_profit,
            return_percent=return_percent,
            initial_cash=result.initial_cash,
            final_cash=result.final_cash,
            open_positions_count=result.open_positions_count,
        )
