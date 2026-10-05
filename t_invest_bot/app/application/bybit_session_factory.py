from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from application.multi_instrument_sandbox_session import MultiInstrumentSandboxSession
from application.multi_instrument_session_config import MultiInstrumentSessionConfig
from application.multi_instrument_session_context import MultiInstrumentSessionContext
from application.portfolio_manager import PortfolioManager
from application.sandbox_trading_session import SandboxTradingSession
from application.trade_capital_service import TradeCapitalService
from application.trade_event_handler import TradeEventHandler
from broker.live_order_manager import LiveOrderManager
from broker.order_execution_event_mapper import OrderExecutionEventMapper
from broker.order_state_tracker import OrderStateTracker
from domain.portfolio import Portfolio
from infrastructure.bybit.client import BybitClient
from infrastructure.bybit.trading import BybitTradingGateway, positive
from portfolio.capital_reservation_manager import CapitalReservationManager
from strategy.grid_builder import GridBuilder
from strategy.grid_engine import GridEngine


@dataclass(slots=True)
class BybitSessionFactory:
    operation_log: Any = None
    notifier: Any = None
    commission_service: Any = None
    knowledge_engine: Any = None

    def create(self, config: MultiInstrumentSessionConfig, credentials, account_id: str, trading_account_id: str, currency: str = "USDT", automatic: bool = False, validate_entry: bool = True) -> MultiInstrumentSessionContext:
        client = BybitClient(credentials.require("api_key"), credentials.require("api_secret"))
        rules: dict[str, dict] = {}
        gateway = BybitTradingGateway(client, rules)
        cash = gateway.get_available_cash(currency)
        if automatic and cash < Decimal("200"):
            raise ValueError("Автоматический Bybit-режим доступен при балансе от 200 USDT")
        if currency != "USDT":
            raise ValueError("Торговые Bybit-сессии поддерживают USDT-пары")
        if not config.instruments or len({item.ticker.upper() for item in config.instruments}) != len(config.instruments):
            raise ValueError("Выберите уникальные активы Bybit")
        portfolio = PortfolioManager(Portfolio(cash=cash))
        capital = TradeCapitalService(portfolio, CapitalReservationManager(available_cash=cash))
        sessions = {}
        for item in config.instruments:
            symbol = item.ticker.strip().upper()
            instruments = client.get_instruments_info(symbol=symbol)
            fees = client.get_fee_rates(symbol)
            if not instruments or not fees:
                raise ValueError(f"Нет правил или фактической комиссии Bybit: {symbol}")
            instrument = instruments[0]
            if instrument.get("status") != "Trading" or instrument.get("quoteCoin") != currency:
                raise ValueError(f"Актив Bybit недоступен для торговли: {symbol}")
            lot = instrument["lotSizeFilter"]
            rule = {
                "base_coin": instrument["baseCoin"], "quote_coin": currency,
                "quantity_step": str(positive(lot["basePrecision"], "quantity step")),
                "min_quantity": str(positive(lot["minOrderQty"], "minimum quantity")),
                "min_order_amount": str(positive(lot["minOrderAmt"], "minimum amount")),
                "price_step": str(positive(instrument["priceFilter"]["tickSize"], "price step")),
            }
            rules[symbol] = rule
            amount = cash * Decimal("0.03") if automatic else item.base_order_amount
            if amount is None:
                raise ValueError(f"Укажите минимальную сумму ордера для {symbol}")
            item.base_order_amount = positive(amount, "base order amount")
            item.quantity_step = Decimal(rule["quantity_step"])
            item.min_quantity = Decimal(rule["min_quantity"])
            item.min_order_amount = Decimal(rule["min_order_amount"])
            if not 2 <= item.levels_count <= 1000:
                raise ValueError("Bybit grid levels must be between 2 and 1000")
            current = gateway.get_mid_price(symbol)
            candles = client.get_klines(symbol=symbol, interval="W", limit=209)
            lows = [positive(row[3], "historical low") for row in candles]
            if len(lows) < 2:
                raise ValueError(f"Недостаточно истории Bybit: {symbol}")
            builder = GridBuilder(levels_count=item.levels_count)
            minimum = min(min(lows), current * Decimal("0.99"))
            engine_config = item.to_grid_engine_config()
            maker = Decimal(str(fees[0]["makerFeeRate"])) * 100
            taker = Decimal(str(fees[0]["takerFeeRate"])) * 100
            if any(not value.is_finite() or value < 0 or value > 100 for value in (maker, taker)):
                raise ValueError("Invalid Bybit asset fee rate")
            engine_config.fallback_buy_commission_percent = max(maker, taker)
            engine_config.fallback_sell_commission_percent = max(maker, taker)
            if validate_entry and engine_config.buy_quantity(current, 0) <= 0:
                raise ValueError(f"Сумма ордера {symbol} не удовлетворяет минимумам/шагам биржи")
            engine = GridEngine(symbol, builder.build_from_range(minimum, current), engine_config, current, builder.calculate_step(minimum, current))
            manager = LiveOrderManager(account_id, gateway, capital)
            handler = TradeEventHandler(
                portfolio_manager=portfolio, knowledge_engine=self.knowledge_engine,
                operation_log=self.operation_log, notifier=self.notifier, ticker=symbol,
                trading_account_id=trading_account_id, commission_service=self.commission_service, broker="bybit",
            )
            sessions[symbol] = SandboxTradingSession(engine, manager, OrderStateTracker(account_id, manager, gateway), OrderExecutionEventMapper(), handler)
        context = MultiInstrumentSessionContext(
            session=MultiInstrumentSandboxSession(sessions), portfolio_manager=portfolio,
            trade_capital_service=capital, price_provider=gateway, sandbox_account_provider=None,
            sandbox_account_id=account_id, sandbox_balance=cash,
            instrument_ids_by_ticker={symbol: symbol for symbol in sessions},
            tickers_by_instrument_id={symbol: symbol for symbol in sessions},
            is_live=True, order_executor=gateway, order_state_provider=gateway,
        )
        return context
