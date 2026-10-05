from __future__ import annotations

import os
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import head_server.app as head_app
from application.head_server_client import HeadReplicationWorker
from application.multi_instrument_session_config import (
    InstrumentConfig,
    MultiInstrumentSessionConfig,
)
from application.trading_settings_service import TradingSettingsService
from application.web_runner_recovery_service import WebRunnerRecoveryService
from head_server.storage import HeadStorage
from web.api import StartPlanInstrumentRequest, _build_multi_instrument_config
import web.api as api_module


@pytest.fixture
def head_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(head_app, "storage", HeadStorage(str(tmp_path / "head.db")))
    return TestClient(head_app.app)


def test_trading_settings_admin_delivery_and_persistence(head_client: TestClient) -> None:
    registered = head_client.post(
        "/head/api/clients/register",
        json={
            "full_name": "Test", "phone": "1", "email": "t@t", "birth_date": "1990-01-01",
            "login": "trader", "password_hash": "hash",
        },
    ).json()
    config_url = "/head/api/config"
    headers = {"X-Api-Key": registered["api_key"]}
    assert head_client.get(config_url).status_code == 401
    assert head_client.get(config_url, headers=headers).json()["trading"]["by_platform"] == {}
    url = "/head/api/admin/trading-settings"
    payload = {
        "platform": "tinvest", "min_profit_percent": "0.5",
        "entry_rebound_percent": "0.2", "trailing_percent": "0.25",
    }
    assert head_client.get(url).status_code == 401
    assert head_client.post(url, json=payload).status_code == 401
    assert head_client.post(
        "/head/api/admin/login",
        json={"login": os.getenv("HEAD_ADMIN_LOGIN", "admin"),
              "password": os.getenv("HEAD_ADMIN_PASSWORD", "esm-admin")},
    ).status_code == 200
    for invalid in (
        {**payload, "platform": "unknown"},
        {**payload, "min_profit_percent": "NaN"},
        {**payload, "trailing_percent": "0"},
        {**payload, "entry_rebound_percent": "101"},
        {**payload, "trailing_percent": "bad"},
    ):
        assert head_client.post(url, json=invalid).status_code == 400
    assert head_client.get(url).json() == {"by_platform": {}}
    assert head_client.post(url, json=payload).status_code == 200
    by_platform = head_client.get(config_url, headers=headers).json()["trading"]["by_platform"]
    assert by_platform == {
        "tinvest": {
            "min_profit_percent": "0.5", "entry_rebound_percent": "0.2",
            "trailing_percent": "0.25",
        }
    }
    assert HeadStorage(head_app.storage.db_path).get_trading_settings() == by_platform
    assert head_client.post(url, json={**payload, "platform": "bybit"}).status_code == 200
    assert len(head_client.get(url).json()["by_platform"]) == 2


def test_growth_settings_admin_delivery_reset_and_restart(head_client, tmp_path):
    endpoint = "/head/api/admin/asset-trading-settings"
    head_client.post("/head/api/admin/login", json={"login": os.getenv("HEAD_ADMIN_LOGIN", "admin"), "password": os.getenv("HEAD_ADMIN_PASSWORD", "esm-admin")})
    payload = {"platform": "bybit", "ticker": "ETHUSDT", "order_amount_multiplier": "1.08", "max_order_amount_multiplier": "2"}
    for invalid in ("NaN", "0.99", "101"):
        assert head_client.post(endpoint, json={**payload, "order_amount_multiplier": invalid}).status_code == 400
    assert head_client.post(endpoint, json=payload).status_code == 200
    values = HeadStorage(head_app.storage.db_path).get_asset_trading_settings()
    assert values["bybit"]["ETHUSDT"]["order_amount_multiplier"] == "1.08"
    local = TradingSettingsService(str(tmp_path / "growth.db"))
    local.apply_head_config({"trading": {"by_platform": {}, "by_asset": values}})
    instrument = TradingSettingsService(local.db_path).apply_to_config(MultiInstrumentSessionConfig([InstrumentConfig("ETHUSDT", 5, 1)]), "bybit").instruments[0]
    assert instrument.order_amount_multiplier == Decimal("1.08")
    assert instrument.max_order_amount_multiplier == Decimal("2")
    with pytest.raises(ValueError):
        local.apply_head_config({"trading": {"by_platform": {}, "by_asset": {"bybit": {"ETHUSDT": {"order_amount_multiplier": "0.9"}}}}})
    assert head_client.post(endpoint, json={"platform": "bybit", "ticker": "ETHUSDT"}).status_code == 200
    reset = HeadStorage(head_app.storage.db_path).get_asset_trading_settings()
    assert reset["bybit"]["ETHUSDT"]["order_amount_multiplier"] is None
    local.apply_head_config({"trading": {"by_platform": {}, "by_asset": reset}})
    default = TradingSettingsService(local.db_path).apply_to_config(MultiInstrumentSessionConfig([InstrumentConfig("ETHUSDT", 5, 1)]), "bybit").instruments[0]
    assert default.order_amount_multiplier == Decimal("1.05")


def test_individual_asset_settings_override_platform_defaults_and_inherit_missing(tmp_path):
    service = TradingSettingsService(str(tmp_path / "asset.db"))
    service.apply_head_config({"trading": {
        "by_platform": {"tinvest": {"min_profit_percent": "0.3", "entry_rebound_percent": "0.2", "trailing_percent": "0.15"}},
        "by_asset": {"tinvest": {"SBER": {"min_profit_percent": "0.7", "trailing_percent": "0.4", "take_profit_percent": "1.2"}}},
    }})
    reloaded = TradingSettingsService(service.db_path)
    config = MultiInstrumentSessionConfig([InstrumentConfig("sber", 5, 1), InstrumentConfig("GAZP", 5, 1)])
    reloaded.apply_to_config(config, "tinvest")
    assert config.instruments[0].min_profit_percent == Decimal("0.7")
    assert config.instruments[0].trailing_percent == Decimal("0.4")
    assert config.instruments[0].entry_rebound_percent == Decimal("0.2")
    assert config.instruments[0].take_profit_percent == Decimal("1.2")
    assert config.instruments[0].to_grid_engine_config().take_profit_percent == Decimal("1.2")
    assert config.instruments[1].take_profit_percent is None
    assert config.instruments[1].min_profit_percent == Decimal("0.3")
    with pytest.raises(ValueError):
        service.apply_head_config({"trading": {"by_platform": {}, "by_asset": {"tinvest": {"SBER": {"trailing_percent": "NaN"}}}}})
    unchanged = reloaded.apply_to_config(MultiInstrumentSessionConfig([InstrumentConfig("SBER", 5, 1)]), "tinvest")
    assert unchanged.instruments[0].trailing_percent == Decimal("0.4")


def test_head_asset_settings_auth_delivery_and_seed_preservation(head_client):
    endpoint = "/head/api/admin/asset-trading-settings"
    assert head_client.get(endpoint).status_code == 401
    assert head_client.post(endpoint, json={"platform": "tinvest", "ticker": "SBER"}).status_code == 401
    head_client.post("/head/api/admin/login", json={"login": os.getenv("HEAD_ADMIN_LOGIN", "admin"), "password": os.getenv("HEAD_ADMIN_PASSWORD", "esm-admin")})
    seeded = head_client.get(endpoint).json()["by_asset"]["bybit"]
    assert seeded["BTCUSDT"]["trailing_percent"] == "0.05"
    assert seeded["BTCUSDT"]["take_profit_percent"] == "1.65"
    assert seeded["ETHUSDT"]["min_profit_percent"] == "0.125"
    payload = {"platform": "tinvest", "ticker": " sber ", "min_profit_percent": "0.9", "trailing_percent": None}
    assert head_client.post(endpoint, json=payload).status_code == 200
    values = HeadStorage(head_app.storage.db_path).get_asset_trading_settings()
    assert values["tinvest"]["SBER"]["min_profit_percent"] == "0.9"
    assert values["tinvest"]["SBER"]["trailing_percent"] is None
    assert head_client.post(endpoint, json={**payload, "min_profit_percent": "NaN"}).status_code == 400
    assert head_client.post(endpoint, json={**payload, "max_take_profit_percent": "NaN"}).status_code == 400
    assert head_client.post(endpoint, json={**payload, "max_take_profit_percent": "3"}).status_code == 200
    assert HeadStorage(head_app.storage.db_path).get_asset_trading_settings()["tinvest"]["SBER"]["max_take_profit_percent"] == "3"


def test_asset_settings_support_future_platform_and_default_fields(head_client, tmp_path):
    head_client.post("/head/api/admin/login", json={"login": os.getenv("HEAD_ADMIN_LOGIN", "admin"), "password": os.getenv("HEAD_ADMIN_PASSWORD", "esm-admin")})
    endpoint = "/head/api/admin/asset-trading-settings"
    payload = {"platform": "future_broker", "ticker": "ASSET", "take_profit_percent": "2", "trailing_percent": "0.6"}
    assert head_client.post(endpoint, json=payload).status_code == 200
    settings = HeadStorage(head_app.storage.db_path).get_asset_trading_settings()
    assert settings["future_broker"]["ASSET"]["entry_rebound_percent"] is None
    local = TradingSettingsService(str(tmp_path / "future.db"))
    local.apply_head_config({"trading": {"by_platform": {}, "by_asset": settings}})
    config = local.apply_to_config(MultiInstrumentSessionConfig([InstrumentConfig("ASSET", 5, 1)]), "future_broker")
    chosen = config.instruments[0]
    assert chosen.take_profit_percent == Decimal("2")
    assert chosen.trailing_percent == Decimal("0.6")
    assert chosen.entry_rebound_percent == InstrumentConfig("ASSET", 5, 1).entry_rebound_percent
    assert head_client.post(endpoint, json={"platform": "future_broker", "ticker": "ASSET"}).status_code == 200
    local.apply_head_config({"trading": {"by_platform": {}, "by_asset": head_client.get(endpoint).json()["by_asset"]}})
    reset = local.apply_to_config(MultiInstrumentSessionConfig([InstrumentConfig("ASSET", 5, 1)]), "future_broker").instruments[0]
    assert reset.take_profit_percent is None
    assert reset.trailing_percent == InstrumentConfig("ASSET", 5, 1).trailing_percent


def test_asset_settings_migrate_old_schema_without_losing_values(tmp_path):
    import sqlite3

    db_path = str(tmp_path / "legacy.db")
    with sqlite3.connect(db_path) as connection:
        connection.execute("CREATE TABLE asset_trading_settings(platform TEXT, ticker TEXT, min_profit_percent TEXT, entry_rebound_percent TEXT, trailing_percent TEXT, PRIMARY KEY(platform, ticker))")
        connection.execute("INSERT INTO asset_trading_settings VALUES ('tinvest', 'SBER', '0.7', NULL, '0.4')")
    service = TradingSettingsService(db_path)
    instrument = service.apply_to_config(MultiInstrumentSessionConfig([InstrumentConfig("SBER", 5, 1)]), "tinvest").instruments[0]
    assert instrument.min_profit_percent == Decimal("0.7")
    assert instrument.trailing_percent == Decimal("0.4")
    assert instrument.take_profit_percent is None
    assert instrument.entry_rebound_percent == InstrumentConfig("SBER", 5, 1).entry_rebound_percent


@pytest.mark.parametrize(("ticker", "trailing", "take_profit"), [
    ("ETHUSDT", "0.1", "0.8"), ("XRPUSDT", "0.1", "0.78"),
    ("BTCUSDT", "0.05", "1.65"), ("LINKUSDT", "0.05", "0.83"),
    ("TONUSDT", "0.1", "0.8"), ("DOTUSDT", "0.1", "0.8"),
    ("BNBUSDT", "0.05", "0.83"), ("SOLUSDT", "0.1", "1.1"),
    ("LTCUSDT", "0.1", "0.8"), ("DOGEUSDT", "0.1", "1.6"),
    ("ARBUSDT", "0.05", "0.65"), ("MNTUSDT", "0.05", "0.65"),
    ("AVAXUSDT", "0.05", "0.65"),
])
def test_legacy_bybit_presets_match_on_head_and_client_after_restart(
    tmp_path: Path, ticker: str, trailing: str, take_profit: str,
) -> None:
    head_path = str(tmp_path / "head.db")
    client_path = str(tmp_path / "client.db")
    HeadStorage(head_path)
    TradingSettingsService(client_path)
    head = HeadStorage(head_path)
    client = TradingSettingsService(client_path)
    expected = {
        "min_profit_percent": "0.125", "entry_rebound_percent": "0.15",
        "trailing_percent": trailing, "take_profit_percent": take_profit,
        "max_take_profit_percent": {"BTCUSDT": "3", "TONUSDT": "3", "DOTUSDT": "3", "LINKUSDT": "10"}.get(ticker, "5"),
        "order_amount_multiplier": "1.05", "max_order_amount_multiplier": "3",
    }
    assert head.get_asset_trading_settings()["bybit"][ticker] == expected
    instrument = client.apply_to_config(
        MultiInstrumentSessionConfig([InstrumentConfig(ticker, 5, 1)]), "bybit",
    ).instruments[0]
    for field, value in expected.items():
        assert getattr(instrument, field) == Decimal(value)


def test_bybit_admin_overrides_and_null_defaults_survive_restart_and_legacy_config(
    tmp_path: Path,
) -> None:
    head = HeadStorage(str(tmp_path / "head.db"))
    head.set_asset_trading_settings(
        "bybit", "BTCUSDT", Decimal("0.9"), None, Decimal("0.4"), Decimal("2.3"),
    )
    head.set_asset_trading_settings("bybit", "ETHUSDT", None, None, None, None)
    expected = head.get_asset_trading_settings()["bybit"]
    assert HeadStorage(head.db_path).get_asset_trading_settings()["bybit"] == expected
    client = TradingSettingsService(str(tmp_path / "client.db"))
    client.apply_head_config({"trading": {
        "by_platform": {}, "by_asset": head.get_asset_trading_settings(),
    }})
    client.apply_head_config({"trading": {"by_platform": {"bybit": {
        "min_profit_percent": "0.5", "entry_rebound_percent": "0.3",
        "trailing_percent": "0.2",
    }}}})
    reloaded = TradingSettingsService(client.db_path)
    btc, eth = reloaded.apply_to_config(MultiInstrumentSessionConfig([
        InstrumentConfig("BTCUSDT", 5, 1), InstrumentConfig("ETHUSDT", 5, 1),
    ]), "bybit").instruments
    assert btc.min_profit_percent == Decimal("0.9")
    assert btc.entry_rebound_percent == Decimal("0.3")
    assert btc.trailing_percent == Decimal("0.4")
    assert btc.take_profit_percent == Decimal("2.3")
    assert eth.min_profit_percent == Decimal("0.5")
    assert eth.entry_rebound_percent == Decimal("0.3")
    assert eth.trailing_percent == Decimal("0.2")
    assert eth.take_profit_percent is None


def test_max_take_profit_migration_preserves_other_overrides_and_explicit_reset(tmp_path: Path) -> None:
    import sqlite3

    for name in ("head", "client"):
        db_path = str(tmp_path / f"{name}.db")
        with sqlite3.connect(db_path) as connection:
            connection.execute("CREATE TABLE asset_trading_settings(platform TEXT, ticker TEXT, min_profit_percent TEXT, entry_rebound_percent TEXT, trailing_percent TEXT, take_profit_percent TEXT, updated_at TEXT NOT NULL DEFAULT '', PRIMARY KEY(platform, ticker))")
            connection.execute("INSERT INTO asset_trading_settings(platform, ticker, min_profit_percent, take_profit_percent) VALUES ('bybit', 'BTCUSDT', '0.9', '2.3')")
        if name == "head":
            storage = HeadStorage(db_path)
            values = storage.get_asset_trading_settings()["bybit"]["BTCUSDT"]
        else:
            TradingSettingsService(db_path)
            with sqlite3.connect(db_path) as connection:
                connection.row_factory = sqlite3.Row
                values = dict(connection.execute("SELECT * FROM asset_trading_settings WHERE platform = 'bybit' AND ticker = 'BTCUSDT'").fetchone())
        assert values["min_profit_percent"] == "0.9"
        assert values["take_profit_percent"] == "2.3"
        assert values["max_take_profit_percent"] == "3"
        with sqlite3.connect(db_path) as connection:
            connection.execute("UPDATE asset_trading_settings SET max_take_profit_percent = NULL WHERE platform = 'bybit' AND ticker = 'BTCUSDT'")
        if name == "head":
            assert HeadStorage(db_path).get_asset_trading_settings()["bybit"]["BTCUSDT"]["max_take_profit_percent"] is None
        else:
            service = TradingSettingsService(db_path)
            instrument = service.apply_to_config(MultiInstrumentSessionConfig([InstrumentConfig("BTCUSDT", 5, 1)]), "bybit").instruments[0]
            assert instrument.max_take_profit_percent is None


def test_client_trading_settings_are_atomic_persistent_and_per_platform(tmp_path: Path) -> None:
    db_path = str(tmp_path / "client.db")
    service = TradingSettingsService(db_path)
    config = {"trading": {"by_platform": {
        "tinvest": {"min_profit_percent": "0.55", "entry_rebound_percent": "0.21",
                    "trailing_percent": "0.16"},
    }}}
    service.apply_head_config(config)
    reloaded = TradingSettingsService(db_path)
    def build() -> MultiInstrumentSessionConfig:
        return MultiInstrumentSessionConfig(instruments=[InstrumentConfig("SBER", 5, 1)])

    chosen = reloaded.apply_to_config(build(), "tinvest").instruments[0]
    assert chosen.min_profit_percent == Decimal("0.55")
    assert chosen.entry_rebound_percent == Decimal("0.21")
    assert chosen.trailing_percent == Decimal("0.16")
    assert reloaded.apply_to_config(build(), "bybit").instruments[0].trailing_percent == Decimal("0.15")
    with pytest.raises(ValueError):
        service.apply_head_config({"trading": {"by_platform": {
            "tinvest": {**config["trading"]["by_platform"]["tinvest"],
                        "trailing_percent": "Infinity"},
        }}})
    assert reloaded.apply_to_config(build(), "tinvest").instruments[0].trailing_percent == Decimal("0.16")
    service.apply_head_config({"commission": {}})
    assert reloaded.apply_to_config(build(), "tinvest").instruments[0].trailing_percent == Decimal("0.16")
    service.apply_head_config({"trading": {"by_platform": {}}})
    assert reloaded.apply_to_config(build(), "tinvest").instruments[0].trailing_percent == Decimal("0.15")


def test_new_session_config_uses_received_platform_settings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = TradingSettingsService(str(tmp_path / "client.db"))
    service.apply_head_config({"trading": {"by_platform": {"tinvest": {
        "min_profit_percent": "0.7", "entry_rebound_percent": "0.3",
        "trailing_percent": "0.4",
    }}}})
    monkeypatch.setattr(api_module, "trading_settings_service", service)
    instruments = [StartPlanInstrumentRequest(ticker="sber", levels=5, quantity=1)]
    chosen = _build_multi_instrument_config(instruments, "tinvest").instruments[0]
    assert chosen.ticker == "SBER"
    assert chosen.min_profit_percent == Decimal("0.7")
    assert chosen.entry_rebound_percent == Decimal("0.3")
    assert chosen.trailing_percent == Decimal("0.4")
    assert _build_multi_instrument_config(instruments, "bybit").instruments[0].trailing_percent == Decimal("0.15")


def test_smlt_asset_rules_override_platform_for_new_and_recovered_sessions(tmp_path, monkeypatch):
    service = TradingSettingsService(str(tmp_path / "smlt-rules.db"))
    service.apply_head_config({"trading": {
        "by_platform": {"tinvest": {"min_profit_percent": "0.3", "entry_rebound_percent": "0.2", "trailing_percent": "0.15"}},
        "by_asset": {"tinvest": {"SMLT": {"min_profit_percent": "0.9", "entry_rebound_percent": "0.6", "trailing_percent": "0.5"}}},
    }})
    monkeypatch.setattr(api_module, "trading_settings_service", TradingSettingsService(service.db_path))
    new = _build_multi_instrument_config([StartPlanInstrumentRequest(ticker="smlt", levels=5, quantity=1)], "tinvest")
    saved = SimpleNamespace(ticker="SMLT", levels=[object()] * 5, open_positions=[], grid_config=None)
    recovered = MultiInstrumentSessionConfig([WebRunnerRecoveryService._build_instrument_config(saved)])
    service.apply_to_config(recovered, "tinvest")
    for config in (new, recovered):
        rules = config.instruments[0].to_grid_engine_config()
        assert rules.min_profit_percent == Decimal("0.9")
        assert rules.entry_rebound_percent == Decimal("0.6")
        assert rules.trailing_percent == Decimal("0.5")


def test_recovered_instrument_uses_current_defaults_not_saved_rules() -> None:
    state = SimpleNamespace(
        ticker="SBER",
        levels=[SimpleNamespace(level_index=1)],
        open_positions=[],
        grid_config=SimpleNamespace(
            quantity=3,
            min_profit_percent=Decimal("9"),
            trailing_percent=Decimal("8"),
            entry_rebound_percent=Decimal("7"),
        ),
    )

    instrument = WebRunnerRecoveryService._build_instrument_config(state)
    defaults = InstrumentConfig("SBER", 1, 3)

    assert instrument.quantity == 3
    assert instrument.min_profit_percent == defaults.min_profit_percent
    assert instrument.trailing_percent == defaults.trailing_percent
    assert instrument.entry_rebound_percent == defaults.entry_rebound_percent


def test_recovery_applies_persisted_head_settings(tmp_path: Path, monkeypatch) -> None:
    service = TradingSettingsService(str(tmp_path / "client.db"))
    service.apply_head_config({"trading": {"by_platform": {"tinvest": {
        "min_profit_percent": "0.7", "entry_rebound_percent": "0.3",
        "trailing_percent": "0.4",
    }}}})
    state = SimpleNamespace(
        session_id="saved", trading_account_id="account", initial_deposit=Decimal("100"),
        status="RUNNING",
        instruments=[SimpleNamespace(ticker="SBER", levels=[object()], open_positions=[], grid_config=None)],
    )
    captured = {}

    def create_context(self, factory, state, config):
        captured["instrument"] = config.instruments[0]
        raise RuntimeError("Stop before broker access")

    monkeypatch.setattr(WebRunnerRecoveryService, "_create_live_context", create_context)
    recovery = WebRunnerRecoveryService(
        settings=api_module.settings,
        state_repository=None,
        state_service=None,
        trading_account_service=None,
        runner_registry=None,
        api_usage_repository=None,
        trading_settings_service=service,
    )

    with pytest.raises(RuntimeError, match="Stop before broker access"):
        recovery._recover_state(state)

    assert captured["instrument"].min_profit_percent == Decimal("0.7")
    assert captured["instrument"].entry_rebound_percent == Decimal("0.3")
    assert captured["instrument"].trailing_percent == Decimal("0.4")


def test_recovery_restores_current_rules_before_reconcile_and_start(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = SimpleNamespace(
        session_id="saved", trading_account_id="account",
        initial_deposit=Decimal("100"), status="RUNNING",
        instruments=[SimpleNamespace(
            ticker="SBER", levels=[object()], open_positions=[], grid_config=None,
        )],
    )
    calls = []
    commission = object()
    operation_log = object()
    handler = SimpleNamespace(trading_account_id="broker-account", broker=None)
    context = SimpleNamespace(
        session=SimpleNamespace(
            poll_executions=lambda: calls.append("poll"),
            sessions={"instrument": SimpleNamespace(trade_event_handler=handler)},
        ),
    )

    def create_context(self, factory, state, config):
        assert factory.commission_service is commission
        assert factory.operation_log is operation_log
        assert factory.broker == "tinvest"
        calls.append("create")
        return context

    def restore(**kwargs):
        assert kwargs["context"] is context
        assert kwargs["session_id"] == "saved"
        assert kwargs["use_current_rules"] is True
        calls.append("restore")
        return state

    def save(**kwargs):
        assert kwargs["context"] is context
        assert kwargs["session_id"] == "saved"
        assert kwargs["status"] == "RUNNING"
        calls.append("save")

    def start(*, runner):
        assert runner.context is context
        assert runner.commission_service is commission
        assert runner.operation_log is operation_log
        assert handler.trading_account_id == "account"
        assert handler.broker == "tinvest"
        assert runner.planned_initial_capital == Decimal("100")
        assert runner.lifecycle_status == "RUNNING"
        calls.append("start")

    monkeypatch.setattr(WebRunnerRecoveryService, "_create_live_context", create_context)
    recovery = WebRunnerRecoveryService(
        settings=api_module.settings,
        state_repository=None,
        state_service=SimpleNamespace(restore=restore, save=save),
        trading_account_service=None,
        runner_registry=SimpleNamespace(start=start, ensure_instruments_available=lambda *args: None),
        api_usage_repository=SimpleNamespace(record=lambda **kwargs: None),
        commission_service=commission,
        operation_log=operation_log,
    )

    recovery._recover_state(state)

    assert calls == ["create", "restore", "poll", "save", "start"]


def test_recovery_overlap_is_rejected_before_creating_context(monkeypatch):
    from application.web_runner_registry import WebRunnerRegistry

    registry = WebRunnerRegistry()
    registry.register(SimpleNamespace(
        session_id="running", trading_account_id="account",
        context=SimpleNamespace(instrument_ids_by_ticker={"SMLT": "smlt-uid"}),
    ))
    state = SimpleNamespace(
        session_id="saved", trading_account_id="account",
        instruments=[SimpleNamespace(ticker="SMLT", levels=[object()], open_positions=[], grid_config=None)],
    )
    monkeypatch.setattr(WebRunnerRecoveryService, "_create_live_context",
        lambda *args, **kwargs: pytest.fail("Overlapping recovery must not access broker positions"))
    recovery = WebRunnerRecoveryService(
        settings=api_module.settings, state_repository=None, state_service=None,
        trading_account_service=None, runner_registry=registry, api_usage_repository=None,
    )
    with pytest.raises(ValueError, match="SMLT"):
        recovery._recover_state(state)
    assert registry.get_all()[0].session_id == "running"


def test_worker_fetches_once_and_applies_trading_without_commission(tmp_path: Path) -> None:
    service = TradingSettingsService(str(tmp_path / "client.db"))
    calls = []
    class FakeClient:
        def fetch_config(self, api_key: str) -> dict:
            calls.append(api_key)
            return {"trading": {"by_platform": {"tinvest": {
                "min_profit_percent": "0.4", "entry_rebound_percent": "0.2",
                "trailing_percent": "0.3",
            }}}}

    worker = HeadReplicationWorker(
        client=FakeClient(), payload_builder=None,
        user_repository=SimpleNamespace(), trading_settings_service=service,
    )
    worker._refresh_head_config("key")
    assert calls == ["key"]
    instrument = InstrumentConfig("SBER", 5, 1)
    service.apply_to_config(MultiInstrumentSessionConfig([instrument]), "tinvest")
    assert instrument.trailing_percent == Decimal("0.3")
