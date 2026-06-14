from dataclasses import dataclass, field
from decimal import Decimal

from broker.order_manager import OrderManager
from broker.virtual_broker import VirtualBroker, VirtualTrade
from domain.entities import Candle
from strategy.grid_engine import GridEngineConfig
from strategy.grid_factory import GridFactory
from strategy.history_analyzer import HistoryAnalyzer, PriceRange


@dataclass(slots=True)
class EquityPoint:
    index: int
    price: Decimal
    equity: Decimal
    drawdown: Decimal
    drawdown_percent: Decimal


@dataclass(slots=True)
class BacktestResult:
    instrument_id: str
    price_range: PriceRange

    initial_cash: Decimal
    final_cash: Decimal
    realized_profit: Decimal

    trades: list[VirtualTrade] = field(default_factory=list)
    open_positions_count: int = 0

    equity_curve: list[EquityPoint] = field(default_factory=list)
    max_drawdown: Decimal = Decimal("0")
    max_drawdown_percent: Decimal = Decimal("0")


@dataclass(slots=True)
class Backtester:
    initial_cash: Decimal = Decimal("100000")

    def run(
        self,
        instrument_id: str,
        history_candles: list[Candle],
        price_series: list[Decimal],
        levels_count: int,
        config: GridEngineConfig,
    ) -> BacktestResult:
        factory = GridFactory(
            history_analyzer=HistoryAnalyzer(exclude_first_days=7),
        )

        factory_result = factory.create_grid_engine(
            instrument_id=instrument_id,
            candles=history_candles,
            levels_count=levels_count,
            config=config,
        )

        engine = factory_result.grid_engine

        broker = VirtualBroker(
            cash=self.initial_cash,
        )

        order_manager = OrderManager(
            broker=broker,
        )

        equity_curve: list[EquityPoint] = []
        peak_equity = self.initial_cash
        max_drawdown = Decimal("0")
        max_drawdown_percent = Decimal("0")

        for index, price in enumerate(price_series):
            commands = engine.on_price(price)
            order_manager.add_commands(commands)

            events = order_manager.process_price(price)

            for event in events:
                engine.on_trade_executed(event)

            equity = broker.calculate_equity(
                current_price=price,
                instrument_id=instrument_id,
            )

            if equity > peak_equity:
                peak_equity = equity

            drawdown = peak_equity - equity

            if peak_equity == Decimal("0"):
                drawdown_percent = Decimal("0")
            else:
                drawdown_percent = drawdown / peak_equity * Decimal("100")

            if drawdown > max_drawdown:
                max_drawdown = drawdown
                max_drawdown_percent = drawdown_percent

            equity_curve.append(
                EquityPoint(
                    index=index,
                    price=price,
                    equity=equity,
                    drawdown=drawdown,
                    drawdown_percent=drawdown_percent,
                )
            )

        return BacktestResult(
            instrument_id=instrument_id,
            price_range=factory_result.price_range,
            initial_cash=self.initial_cash,
            final_cash=broker.cash,
            realized_profit=broker.realized_profit,
            trades=broker.trades,
            open_positions_count=len(engine.open_positions),
            equity_curve=equity_curve,
            max_drawdown=max_drawdown,
            max_drawdown_percent=max_drawdown_percent,
        )
