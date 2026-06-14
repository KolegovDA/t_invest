from dataclasses import dataclass, field
from decimal import Decimal

from broker.order_manager import OrderManager
from broker.virtual_broker import VirtualBroker, VirtualTrade
from domain.entities import Candle
from strategy.grid_engine import GridEngineConfig
from strategy.grid_factory import GridFactory
from strategy.history_analyzer import HistoryAnalyzer, PriceRange


@dataclass(slots=True)
class BacktestResult:
    instrument_id: str
    price_range: PriceRange

    initial_cash: Decimal
    final_cash: Decimal
    realized_profit: Decimal

    trades: list[VirtualTrade] = field(default_factory=list)
    open_positions_count: int = 0


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

        for price in price_series:
            commands = engine.on_price(price)
            order_manager.add_commands(commands)

            events = order_manager.process_price(price)

            for event in events:
                engine.on_trade_executed(event)

        return BacktestResult(
            instrument_id=instrument_id,
            price_range=factory_result.price_range,
            initial_cash=self.initial_cash,
            final_cash=broker.cash,
            realized_profit=broker.realized_profit,
            trades=broker.trades,
            open_positions_count=len(engine.open_positions),
        )
