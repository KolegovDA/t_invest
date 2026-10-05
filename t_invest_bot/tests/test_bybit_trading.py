from decimal import Decimal
from types import SimpleNamespace

import pytest

from application.bybit_session_factory import BybitSessionFactory
from application.multi_instrument_session_config import InstrumentConfig, MultiInstrumentSessionConfig
from infrastructure.bybit.trading import BybitTradingGateway


class FakeBybitClient:
    def __init__(self, *args):
        self.orders = []
        self.balance = "300"
        self.fills = []
        self.order_rows = []

    def get_wallet_balance(self):
        return {"coin": [{"coin": "USDT", "walletBalance": self.balance, "locked": "0"}]}

    def get_tickers(self, symbol):
        return [{"bid1Price": "99.9", "ask1Price": "100.1", "lastPrice": "100"}]

    def get_instruments_info(self, symbol):
        return [{"symbol": symbol, "status": "Trading", "baseCoin": "ETH", "quoteCoin": "USDT",
                 "lotSizeFilter": {"basePrecision": "0.0001", "minOrderQty": "0.0001", "minOrderAmt": "5"},
                 "priceFilter": {"tickSize": "0.01"}}]

    def get_fee_rates(self, symbol):
        return [{"makerFeeRate": "0.001", "takerFeeRate": "0.002"}]

    def get_klines(self, **kwargs):
        return [["1", "100", "110", "60", "100"], ["2", "100", "110", "70", "100"]]

    def place_spot_order(self, body):
        self.orders.append(body)
        return {"orderId": "order-1"}

    def get_spot_orders(self, **kwargs):
        return self.order_rows

    def get_spot_executions(self, order_id):
        return self.fills


RULE = {"quantity_step": "0.0001", "min_quantity": "0.0001", "min_order_amount": "5", "price_step": "0.01", "base_coin": "ETH", "quote_coin": "USDT"}


def test_bybit_limit_and_market_are_nonleveraged_spot_with_exact_quantity():
    client = FakeBybitClient()
    gateway = BybitTradingGateway(client, {"ETHUSDT": RULE})
    gateway.place_limit_buy("account", "ETHUSDT", Decimal("0.06"), Decimal("100.009"))
    assert client.orders[0]["price"] == "100.00"
    assert client.orders[0]["qty"] == "0.06"
    assert client.orders[0]["isLeverage"] == 0
    gateway.place_market_sell("account", "ETHUSDT", Decimal("0.06"))
    assert client.orders[1]["marketUnit"] == "baseCoin"
    assert client.orders[1]["orderType"] == "Market"
    assert "price" not in client.orders[1]
    with pytest.raises(ValueError):
        gateway.place_limit_buy("account", "ETHUSDT", Decimal("0.00011"), Decimal("100"))
    assert len(client.orders) == 2


def test_bybit_cancelled_partial_execution_is_applied_once_without_fractional_loss(monkeypatch):
    import application.bybit_session_factory as module
    from broker.live_order_manager import LiveOrderRecord
    from domain.commands import PlaceBuyLimitCommand
    from domain.order_execution import PlacedOrder

    client = FakeBybitClient()
    monkeypatch.setattr(module, "BybitClient", lambda *args: client)
    context = BybitSessionFactory().create(
        MultiInstrumentSessionConfig([InstrumentConfig("ETHUSDT", 5, 1, base_order_amount=Decimal("6"))]),
        SimpleNamespace(require=lambda _: "test"), "broker", "internal",
    )
    trading = context.session.sessions["ETHUSDT"]
    trading.live_order_manager.active_orders["order-1"] = LiveOrderRecord(
        PlaceBuyLimitCommand("ETHUSDT", 1, Decimal("0.06"), Decimal("100")), PlacedOrder("order-1"),
    )
    client.order_rows = [{"orderId": "order-1", "symbol": "ETHUSDT", "side": "Buy", "orderStatus": "PartiallyFilledCanceled", "cumExecQty": "0.02", "cumExecValue": "2"}]
    client.fills = [{"execId": "fill-1", "execQty": "0.02", "execFee": "0.00002", "feeCurrency": "ETH", "execPrice": "100"}]
    events = trading.poll_executions()
    assert len(events) == 1
    assert trading.grid_engine.open_positions[1].quantity == Decimal("0.01998")
    assert trading.grid_engine.open_positions[1].purchase_cost == Decimal("2")
    assert trading.poll_executions() == []
    assert not trading.live_order_manager.active_orders
    assert client.orders == []


def test_bybit_sell_rounds_owned_quantity_down_without_selling_extra_assets():
    client = FakeBybitClient()
    gateway = BybitTradingGateway(client, {"ETHUSDT": RULE})
    gateway.place_market_sell("account", "ETHUSDT", Decimal("0.05994"))
    assert client.orders[0]["qty"] == "0.0599"
    with pytest.raises(ValueError, match="остаток"):
        gateway.place_market_sell("account", "ETHUSDT", Decimal("0.00004"))
    assert len(client.orders) == 1


def test_bybit_start_api_uses_connected_account_without_tinvest_token(monkeypatch):
    from fastapi.testclient import TestClient
    import application.bybit_session_factory as factory_module
    import web.api as api_module
    from domain.trading_account import BrokerType, TradingAccount, TradingAccountMode

    client = FakeBybitClient()
    monkeypatch.setattr(factory_module, "BybitClient", lambda *args: client)
    account = TradingAccount(id="bybit-1", name="Bybit", broker=BrokerType.BYBIT, broker_account_id="uid", mode=TradingAccountMode.LIVE, base_currency="USDT")
    monkeypatch.setattr(api_module, "trading_account_service", SimpleNamespace(get=lambda _: account, get_credentials=lambda _: SimpleNamespace(require=lambda _: "test")))
    monkeypatch.setattr(api_module.settings, "trading_mode", "sandbox")
    monkeypatch.setattr(api_module.settings, "live_trading_enabled", False)
    monkeypatch.setattr(api_module.settings, "tinvest_token", None)
    monkeypatch.setattr(api_module.settings, "tinvest_live_account_id", None)
    monkeypatch.setattr(api_module, "head_replication_worker", SimpleNamespace(_current_api_key=lambda: None))
    monkeypatch.setattr(api_module, "commission_service", SimpleNamespace(is_forced_drain=lambda: False))
    runners = []
    monkeypatch.setattr(api_module, "web_runner_registry", SimpleNamespace(start=lambda runner: runners.append(runner), has_session_id=lambda _: False, ensure_instruments_available=lambda *args: None))
    response = TestClient(api_module.app).post("/api/start-live", json={"trading_account_id": account.id, "bybit_automatic": True, "instruments": [{"ticker": "ETHUSDT", "levels": 5, "quantity": 1}]})
    assert response.status_code == 200, response.text
    assert response.json()["broker"] == "bybit"
    assert len(runners) == 1
    assert runners[0].context.session.sessions["ETHUSDT"].grid_engine.config.base_order_amount == Decimal("9")
    assert client.orders == []


@pytest.mark.parametrize("mode,enabled", [("sandbox", True), ("live", False)])
def test_bybit_start_rejects_non_live_or_disabled_account(monkeypatch, mode, enabled):
    from fastapi.testclient import TestClient
    import web.api as api_module
    from domain.trading_account import BrokerType, TradingAccount, TradingAccountMode

    account = TradingAccount(id="bybit-reject", name="Bybit", broker=BrokerType.BYBIT,
        broker_account_id="uid", mode=TradingAccountMode(mode), enabled=enabled)
    monkeypatch.setattr(api_module, "trading_account_service", SimpleNamespace(
        get=lambda _: account,
        get_credentials=lambda _: pytest.fail("Rejected accounts must not load credentials"),
    ))
    monkeypatch.setattr(api_module, "head_replication_worker", SimpleNamespace(_current_api_key=lambda: None))
    monkeypatch.setattr(api_module, "commission_service", SimpleNamespace(is_forced_drain=lambda: False))
    monkeypatch.setattr(api_module, "BybitSessionFactory", lambda **kwargs: pytest.fail("Rejected accounts must not create a session"))
    response = TestClient(api_module.app).post("/api/start-live", json={
        "trading_account_id": account.id, "instruments": [{"ticker": "ETHUSDT", "levels": 5, "quantity": 1}],
    })
    assert response.status_code == 400
    assert response.json()["detail"] == "Выберите активный боевой счёт Bybit"


@pytest.mark.parametrize("check_fails,status", [(False, 403), (True, 503)])
def test_bybit_start_rejects_forced_drain_or_unavailable_commission_check(monkeypatch, check_fails, status):
    from fastapi.testclient import TestClient
    import web.api as api_module
    from domain.trading_account import BrokerType, TradingAccount, TradingAccountMode

    account = TradingAccount(id="bybit-drain", name="Bybit", broker=BrokerType.BYBIT,
        broker_account_id="uid", mode=TradingAccountMode.LIVE)

    def is_forced_drain():
        if check_fails:
            raise RuntimeError("Commission storage is unavailable")
        return True

    monkeypatch.setattr(api_module.settings, "trading_mode", "sandbox")
    monkeypatch.setattr(api_module.settings, "live_trading_enabled", False)
    monkeypatch.setattr(api_module, "head_replication_worker", SimpleNamespace(_current_api_key=lambda: None))
    monkeypatch.setattr(api_module, "commission_service", SimpleNamespace(is_forced_drain=is_forced_drain))
    monkeypatch.setattr(api_module, "trading_account_service", SimpleNamespace(
        get=lambda _: account,
        get_credentials=lambda _: pytest.fail("Blocked starts must not load credentials"),
    ))
    monkeypatch.setattr(api_module, "BybitSessionFactory", lambda **kwargs: pytest.fail("Blocked starts must not create a session"))
    monkeypatch.setattr(api_module, "web_runner_registry", SimpleNamespace(
        start=lambda **kwargs: pytest.fail("Blocked starts must not start a runner"),
        ensure_instruments_available=lambda *args: None,
    ))
    response = TestClient(api_module.app).post("/api/start-live", json={
        "trading_account_id": account.id, "instruments": [{"ticker": "ETHUSDT", "levels": 5, "quantity": 1}],
    })
    assert response.status_code == status
    expected = "Не удалось проверить разрешение запуска" if check_fails else "ЛК-баланс отрицательный"
    assert expected in response.json()["detail"]


def test_bybit_recovery_preserves_fractional_positions_and_pending_market_sell(tmp_path, monkeypatch):
    import application.bybit_session_factory as factory_module
    import application.web_runner_recovery_service as recovery_module
    from application.trading_session_state_service import TradingSessionStateService
    from application.trading_settings_service import TradingSettingsService
    from application.web_runner_recovery_service import WebRunnerRecoveryService
    from broker.live_order_manager import LiveOrderRecord
    from domain.commands import PlaceSellLimitCommand
    from domain.events import TradeExecutedEvent
    from domain.order_execution import PlacedOrder
    from domain.trading_account import BrokerType, TradingAccount, TradingAccountMode
    from infrastructure.sqlite.trading_state_repository import TradingStateRepository

    client = FakeBybitClient()
    monkeypatch.setattr(factory_module, "BybitClient", lambda *args: client)
    context = BybitSessionFactory().create(
        MultiInstrumentSessionConfig([InstrumentConfig("ETHUSDT", 5, 1, base_order_amount=Decimal("6"))]),
        SimpleNamespace(require=lambda _: "test"), "broker", "internal",
    )
    trading = context.session.sessions["ETHUSDT"]
    trading.grid_engine.on_trade_executed(TradeExecutedEvent("ETHUSDT", 1, "BUY", Decimal("0.06"), Decimal("100")))
    trading.live_order_manager.active_orders["pending"] = LiveOrderRecord(
        PlaceSellLimitCommand("ETHUSDT", 1, Decimal("0.06"), Decimal("100"), is_market=True),
        PlacedOrder("pending", "request"),
    )
    repository = TradingStateRepository(str(tmp_path / "recovery.db"))
    state_service = TradingSessionStateService(repository)
    state_service.save(context, "saved", "internal", status="STOPPING")
    settings_service = TradingSettingsService(str(tmp_path / "rules.db"))
    settings_service.apply_head_config({"trading": {"by_platform": {}, "by_asset": {"bybit": {"ETHUSDT": {"trailing_percent": "0.2", "order_amount_multiplier": "1.08"}}}}})
    account = TradingAccount(id="internal", name="Bybit", broker=BrokerType.BYBIT, broker_account_id="broker", mode=TradingAccountMode.LIVE, base_currency="USDT")
    client.balance = "0"
    client.get_instruments_info = lambda symbol: [{"symbol": symbol, "status": "Trading", "baseCoin": "ETH", "quoteCoin": "USDT", "lotSizeFilter": {"basePrecision": "0.0001", "minOrderQty": "0.0001", "minOrderAmt": "10"}, "priceFilter": {"tickSize": "0.01"}}]
    runners = []
    monkeypatch.setattr(recovery_module, "WebRunnerService", lambda **kwargs: SimpleNamespace(**kwargs))
    recovery = WebRunnerRecoveryService(
        settings=SimpleNamespace(), state_repository=repository, state_service=state_service,
        trading_account_service=SimpleNamespace(get=lambda _: account, get_credentials=lambda _: SimpleNamespace(require=lambda _: "test")),
        runner_registry=SimpleNamespace(has_session_id=lambda _: False, start=lambda **kwargs: runners.append(kwargs["runner"]), ensure_instruments_available=lambda *args: None),
        api_usage_repository=SimpleNamespace(record=lambda **kwargs: None), trading_settings_service=settings_service,
    )
    result = recovery.recover_active_runners()
    assert result.restored == 1 and result.failed == 0
    restored = runners[0].context.session.sessions["ETHUSDT"]
    assert runners[0].lifecycle_status == "STOPPING"
    assert restored.grid_engine.open_positions[1].quantity == Decimal("0.06")
    assert restored.grid_engine.config.base_order_amount == Decimal("6")
    assert restored.grid_engine.config.order_amount_multiplier == Decimal("1.08")
    assert restored.grid_engine.config.trailing_percent == Decimal("0.2")
    assert restored.grid_engine.config.min_order_amount == Decimal("10")
    assert restored.live_order_manager.active_orders["pending"].command.is_market
    assert client.orders == []


def test_bybit_recovery_keys_do_not_truncate_fractional_quantity_or_order_budget():
    from application.web_runner_recovery_service import WebRunnerRecoveryService

    def key(quantity, amount):
        return WebRunnerRecoveryService._build_recovery_key(SimpleNamespace(
            trading_account_id="account", broker_account_id="broker", mode="live",
            instruments=[SimpleNamespace(ticker="ETHUSDT", levels=[object()], grid_config=SimpleNamespace(quantity=quantity, base_order_amount=amount))],
        ))

    assert key(Decimal("0.1"), Decimal("6")) != key(Decimal("0.2"), Decimal("6"))
    assert key(1, Decimal("6")) != key(1, Decimal("9"))


def test_bybit_buy_base_coin_fee_reduces_owned_quantity_and_preserves_cost():
    client = FakeBybitClient()
    client.order_rows = [{"orderId": "order-1", "symbol": "ETHUSDT", "side": "Buy", "orderStatus": "Filled", "cumExecQty": "0.06", "cumExecValue": "6"}]
    client.fills = [{"execId": "fill-1", "execQty": "0.06", "execFee": "0.00006", "feeCurrency": "ETH", "execPrice": "100"}]
    state = BybitTradingGateway(client, {"ETHUSDT": RULE}).get_order_state("account", "order-1")
    assert state.is_executed
    assert state.executed_quantity == Decimal("0.05994")
    assert state.executed_commission == Decimal("0.006")
    assert state.total_order_amount + state.executed_commission == Decimal("6")


def test_bybit_missing_executions_do_not_acknowledge_terminal_fill():
    client = FakeBybitClient()
    client.order_rows = [{"orderId": "order-1", "symbol": "ETHUSDT", "side": "Buy", "orderStatus": "Filled", "cumExecQty": "0.06", "cumExecValue": "6"}]
    state = BybitTradingGateway(client, {"ETHUSDT": RULE}).get_order_state("account", "order-1")
    assert not state.is_executed
    assert state.status == "UNKNOWN"


@pytest.mark.parametrize("balance,amount", [("200", "6"), ("300", "9"), ("400", "12")])
def test_bybit_factory_uses_main_engine_proportional_sizing_and_actual_asset_fees(monkeypatch, balance, amount):
    import application.bybit_session_factory as module

    client = FakeBybitClient()
    client.balance = balance
    monkeypatch.setattr(module, "BybitClient", lambda *args: client)
    context = BybitSessionFactory().create(
        MultiInstrumentSessionConfig([InstrumentConfig("ETHUSDT", 5, 1)]),
        SimpleNamespace(require=lambda name: "test"), "broker", "internal", automatic=True,
    )
    engine = context.session.sessions["ETHUSDT"].grid_engine
    assert engine.config.base_order_amount == Decimal(amount)
    assert engine.config.fallback_buy_commission_percent == Decimal("0.2")
    assert engine.config.quantity_step == Decimal("0.0001")
    assert context.session.sessions["ETHUSDT"].trade_event_handler.broker == "bybit"
    assert client.orders == []


@pytest.mark.parametrize("amount,valid", [("6", True), ("4.99", False)])
def test_bybit_manual_budget_checks_exchange_minimum_without_placing_orders(monkeypatch, amount, valid):
    import application.bybit_session_factory as module

    client = FakeBybitClient()
    monkeypatch.setattr(module, "BybitClient", lambda *args: client)
    config = MultiInstrumentSessionConfig([InstrumentConfig("ETHUSDT", 5, 1, base_order_amount=Decimal(amount))])
    if valid:
        context = BybitSessionFactory().create(config, SimpleNamespace(require=lambda _: "test"), "broker", "internal")
        assert context.session.sessions["ETHUSDT"].grid_engine.config.base_order_amount == Decimal(amount)
    else:
        with pytest.raises(ValueError, match="минимумам"):
            BybitSessionFactory().create(config, SimpleNamespace(require=lambda _: "test"), "broker", "internal")
    assert client.orders == []


def test_bybit_auto_below_200_is_rejected_without_orders(monkeypatch):
    import application.bybit_session_factory as module

    client = FakeBybitClient()
    client.balance = "199.99"
    monkeypatch.setattr(module, "BybitClient", lambda *args: client)
    with pytest.raises(ValueError, match="200"):
        BybitSessionFactory().create(MultiInstrumentSessionConfig([InstrumentConfig("ETHUSDT", 5, 1)]), SimpleNamespace(require=lambda name: "test"), "broker", "internal", automatic=True)
    assert client.orders == []
