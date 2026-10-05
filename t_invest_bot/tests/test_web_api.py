from dataclasses import dataclass, field
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from decimal import Decimal
from types import SimpleNamespace

import pytest

from domain.entities import Candle
from domain.enums import GridLevelStatus
from domain.trading_account import (
    BrokerType,
    TradingAccount,
    TradingAccountMode,
)
from fastapi.testclient import TestClient

from application.sandbox_session_registry import (
    sandbox_session_registry,
)
from domain.balance_snapshot import (
    BalanceSnapshot,
)
from domain.broker_cash_flow import (
    BrokerCashFlow,
)
from domain.operation_event import (
    OperationEvent,
)
from infrastructure.sqlite.commission_repository import (
    CommissionCharge,
)
import web.api as api_module

from web.api import (
    app,
    session_registry,
    settings,
)


def setup_function() -> None:
    session_registry.sessions.clear()
    sandbox_session_registry.sessions.clear()


def test_dashboard_history_returns_total_line_in_rubles(monkeypatch):
    monkeypatch.setattr(api_module, "dashboard", lambda: {
        "total_equity": 1100, "available_cash": 1000, "total_balance": 10000,
        "total_balance_currency": "RUB", "exchange_rates_rub": {"RUB": 1, "USDT": 90},
        "accounts_detail": [
            {"id": "a", "name": "T-Invest", "broker": "tinvest", "currency": "RUB", "balance": 1000},
            {"id": "b", "name": "Bybit", "broker": "bybit", "currency": "USDT", "balance": 100},
        ],
    })
    monkeypatch.setattr(api_module, "balance_snapshot_repository", SimpleNamespace(
        get_since=lambda **kwargs: [], get_first_by_currency=lambda: {},
    ))
    monkeypatch.setattr(api_module, "trading_account_service", SimpleNamespace(get_all=lambda: []))
    result = api_module.dashboard_history()
    assert result["total_points"][-1]["equity"] == 10000
    assert result["total_balance_currency"] == "RUB"
    assert "текущему курсу" in result["history_note"]


def test_total_balance_converts_two_platforms_without_adding_currency_units(monkeypatch):
    monkeypatch.setattr(api_module, "_usd_rub_rate", lambda: Decimal("90"))
    accounts = [
        {"broker": "tinvest", "currency": "RUB", "balance": 1000, "enabled": True},
        {"broker": "bybit", "currency": "USDT", "balance": 100, "enabled": True},
    ]
    result = api_module._dashboard_total_balance(accounts)
    assert result["total_balance"] == 10000
    assert result["total_balance_currency"] == "RUB"
    assert api_module._dashboard_total_balance(accounts[1:])["total_balance"] == 100
    assert api_module._dashboard_total_balance(accounts[1:])["total_balance_currency"] == "USDT"
    monkeypatch.setattr(api_module, "_usd_rub_rate", lambda: None)
    assert api_module._dashboard_total_balance(accounts)["total_balance"] is None


def test_snapshot_timestamp_accepts_missing_and_invalid_values() -> None:
    assert api_module._parse_snapshot_timestamp(None) is None
    assert api_module._parse_snapshot_timestamp("invalid") is None
    assert api_module._parse_snapshot_timestamp("2026-10-04T12:00:00") == datetime(2026, 10, 4, 12, tzinfo=timezone.utc)


def test_bybit_asset_rules_endpoint_checks_adapter_capability(monkeypatch) -> None:
    account = SimpleNamespace(broker=BrokerType.BYBIT, mode=TradingAccountMode.LIVE, enabled=True)
    credentials = object()
    monkeypatch.setattr(api_module, "trading_account_service", SimpleNamespace(
        get=lambda _: account, get_credentials=lambda _: credentials,
    ))
    monkeypatch.setattr(api_module, "broker_registry", SimpleNamespace(get=lambda _: object()))
    client = TestClient(app)
    assert client.get("/api/bybit/accounts/account/asset-rules/btcusdt").status_code == 400
    calls = []

    def asset_rules(supplied_credentials, symbol):
        calls.append((supplied_credentials, symbol))
        return {"min_order_amount": "5"}

    monkeypatch.setattr(api_module, "broker_registry", SimpleNamespace(
        get=lambda _: SimpleNamespace(asset_rules=asset_rules),
    ))
    response = client.get("/api/bybit/accounts/account/asset-rules/btcusdt")
    assert response.status_code == 200
    assert response.json()["min_order_amount"] == "5"
    assert calls == [(credentials, "BTCUSDT")]


def test_health_endpoint_returns_ok() -> None:
    client = TestClient(app)

    response = client.get(
        "/api/health"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"
    assert "trading_mode" in data
    assert "live_trading_enabled" in data
    assert "real_sandbox_enabled" in data


def test_version_endpoint_returns_version() -> None:
    client = TestClient(app)

    response = client.get(
        "/api/version"
    )

    assert response.status_code == 200

    assert (
        response.json()["version"]
        == (
            api_module
            .APP_VERSION
        )
    )


def test_dashboard_endpoint_returns_dashboard() -> None:
    client = TestClient(app)

    response = client.get(
        "/api/dashboard"
    )

    assert response.status_code == 200

    data = response.json()

    assert "accounts" in data
    assert "capital" in data
    assert "total_equity" in data
    assert "available_cash" in data
    assert "available_cash_by_currency" in data
    assert "invested_cash_by_currency" in data
    assert "reserved_cash" in data
    assert "active_positions" in data
    assert "profit" in data
    assert "instruments" in data

    assert (
        data["available_cash_by_currency"]
        == {}
        or isinstance(
            data[
                "available_cash_by_currency"
            ],
            dict,
        )
    )

    assert isinstance(
        data[
            "invested_cash_by_currency"
        ],
        dict,
    )

    assert (
        data["accounts"]
        >= 0
    )

    #
    # Р’ С‚РµСЃС‚РѕРІРѕР№ Р‘Р” РјРѕР¶РµС‚ РЅРµ Р±С‹С‚СЊ
    # Р°РєС‚РёРІРЅРѕР№ С‚РѕСЂРіРѕРІРѕР№ СЃРµСЃСЃРёРё.
    #
    if data["accounts"] == 0:
        assert (
            data["capital"]
            is None
        )

        assert (
            data["available_cash"]
            is None
        )

        assert (
            data["reserved_cash"]
            is None
        )


def test_dashboard_prefers_current_broker_equity(monkeypatch) -> None:
    account = TradingAccount(
        id="account-1",
        name="Main",
        broker=BrokerType.TINVEST,
        broker_account_id="broker-1",
        mode=TradingAccountMode.LIVE,
    )
    monkeypatch.setattr(
        api_module,
        "trading_account_service",
        SimpleNamespace(
            get_all=lambda: [account],
            get_credentials=lambda account_id: SimpleNamespace(),
        ),
    )
    monkeypatch.setattr(
        api_module,
        "trading_state_repository",
        SimpleNamespace(get_active=lambda: []),
    )
    monkeypatch.setattr(
        api_module,
        "web_runner_registry",
        SimpleNamespace(get_all=lambda: []),
    )
    monkeypatch.setattr(
        api_module,
        "broker_registry",
        SimpleNamespace(
            get=lambda broker: SimpleNamespace(
                get_portfolio=lambda **kwargs: SimpleNamespace(
                    cash=Decimal("60"),
                    total_value=Decimal("85"),
                ),
            ),
        ),
    )
    monkeypatch.setattr(
        api_module,
        "balance_snapshot_repository",
        SimpleNamespace(
            get_since=lambda **kwargs: [
                BalanceSnapshot(
                    created_at=datetime.now(timezone.utc).isoformat(),
                    trading_account_id=account.id,
                    currency="RUB",
                    equity=Decimal("100"),
                ),
            ],
        ),
    )

    result = api_module.dashboard()

    assert result["total_equity"] == 85.0
    assert result["accounts_detail"][0]["balance"] == 85.0
    assert result["available_cash"] == 60.0


def test_dashboard_history_uses_current_account_balance(monkeypatch) -> None:
    moment = datetime.now(timezone.utc)
    monkeypatch.setattr(
        api_module,
        "dashboard",
        lambda: {
            "total_equity": 65.0,
            "available_cash": 60.0,
            "accounts_detail": [
                {"id": "account-1", "currency": "RUB", "balance": 65.0},
            ],
        },
    )
    monkeypatch.setattr(
        api_module,
        "balance_snapshot_repository",
        SimpleNamespace(
            get_since=lambda **kwargs: [
                BalanceSnapshot(
                    created_at=(moment - timedelta(hours=1)).isoformat(),
                    trading_account_id="account-1",
                    currency="RUB",
                    equity=Decimal("100"),
                ),
            ],
            get_first_by_currency=lambda: {},
        ),
    )

    result = api_module.dashboard_history(days=30)

    assert result["equity_by_currency"] == {"RUB": 65.0}
    assert result["points_by_account"]["account-1"][-1]["equity"] == 65.0
    assert result["days"] == 30


def test_dashboard_history_does_not_reconstruct_unknown_equity(monkeypatch):
    moment = datetime.now(timezone.utc)
    monkeypatch.setattr(api_module, "dashboard", lambda: {
        "total_equity": 100.0, "available_cash": 100.0,
        "accounts_detail": [{"id": "account-1", "currency": "RUB", "balance": 100.0}],
    })
    monkeypatch.setattr(api_module, "balance_snapshot_repository", SimpleNamespace(
        get_since=lambda **kwargs: [BalanceSnapshot(
            moment.isoformat(), "account-1", "RUB", Decimal("100"),
        )],
        get_first_by_currency=lambda: {},
    ))
    result = api_module.dashboard_history(days=180)
    assert all(datetime.fromisoformat(point["ts"]) >= moment for point in result["points"])
    assert all(datetime.fromisoformat(point["ts"]) >= moment for point in result["points_by_currency"]["RUB"])
    assert result["history_note"]


def test_dashboard_history_includes_accounts_without_saved_snapshots(monkeypatch) -> None:
    moment = datetime.now(timezone.utc)
    monkeypatch.setattr(api_module, "dashboard", lambda: {
        "total_equity": 125.0,
        "accounts_detail": [
            {"id": "account-1", "currency": "RUB", "balance": 100.0},
            {"id": "bybit-1", "currency": "USDT", "balance": 25.0},
            {"id": "unavailable", "currency": "USDT", "balance": None},
        ],
    })
    monkeypatch.setattr(api_module, "balance_snapshot_repository", SimpleNamespace(
        get_since=lambda **kwargs: [BalanceSnapshot(
            (moment - timedelta(hours=1)).isoformat(), "account-1", "RUB", Decimal("90"),
        )],
        get_first_by_currency=lambda: {},
    ))
    result = api_module.dashboard_history(days=180)
    assert result["points_by_account"]["account-1"][-1]["equity"] == 100.0
    assert len(result["points_by_account"]["bybit-1"]) == 1
    point = result["points_by_account"]["bybit-1"][0]
    assert point["equity"] == 25.0
    assert datetime.fromisoformat(point["ts"]) >= moment
    assert "unavailable" not in result["points_by_account"]
    assert {account["id"] for account in result["accounts"]} == {"account-1", "bybit-1"}


def test_dashboard_history_returns_current_only_account_without_fabricating_history(monkeypatch) -> None:
    moment = datetime.now(timezone.utc)
    monkeypatch.setattr(api_module, "dashboard", lambda: {
        "total_equity": 0.0,
        "accounts_detail": [{"id": "bybit-1", "currency": "USDT", "balance": 0.0}],
    })
    monkeypatch.setattr(api_module, "balance_snapshot_repository", SimpleNamespace(
        get_since=lambda **kwargs: [],
        get_first_by_currency=lambda: {},
    ))
    result = api_module.dashboard_history(days=180)
    assert len(result["points_by_account"]["bybit-1"]) == 1
    assert result["points_by_account"]["bybit-1"][0]["equity"] == 0.0
    assert datetime.fromisoformat(result["points_by_account"]["bybit-1"][0]["ts"]) >= moment
    assert result["points_by_currency"]["USDT"] == result["points_by_account"]["bybit-1"]
    assert result["points"] == result["points_by_account"]["bybit-1"]
    assert result["accounts"] == [{"id": "bybit-1", "name": "bybit-1", "currency": "USDT", "broker": None}]


def test_dashboard_history_filters_selected_period(monkeypatch) -> None:
    moment = datetime.now(timezone.utc)
    snapshots = [
        BalanceSnapshot(
            created_at=(moment - timedelta(days=age)).isoformat(),
            trading_account_id="account-1",
            currency="RUB",
            equity=Decimal("100"),
        )
        for age in (120, 60, 20, 2)
    ]
    requested_since = []

    def get_since(since):
        requested_since.append(datetime.fromisoformat(since))
        return [snapshot for snapshot in snapshots if snapshot.created_at >= since]

    monkeypatch.setattr(
        api_module,
        "dashboard",
        lambda: {"total_equity": 100.0, "available_cash": 100.0},
    )
    monkeypatch.setattr(
        api_module,
        "balance_snapshot_repository",
        SimpleNamespace(get_since=get_since, get_first_by_currency=lambda: {}),
    )

    for days, expected_snapshots in ((7, 1), (30, 2), (90, 3), (180, 4), (15, 1)):
        result = api_module.dashboard_history(days=days)
        normalized_days = 7 if days == 15 else days
        assert result["days"] == normalized_days
        assert len(result["points_by_account"]["account-1"]) == expected_snapshots + 1
        assert abs((moment - requested_since[-1]).total_seconds() / 86400 - normalized_days) < 0.01


def test_dashboard_history_uses_balance_snapshots(
    monkeypatch,
) -> None:
    moment = (
        datetime
        .now(
            timezone.utc,
        )
    )

    base = (
        moment
        - timedelta(
            days=2,
        )
    )

    class FakeBalanceSnapshotRepository:
        def __init__(
            self,
            snapshots,
        ):
            self.snapshots = (
                snapshots
            )

        def get_since(
            self,
            since,
        ):
            return (
                self
                .snapshots
            )

    snapshots = [
        BalanceSnapshot(
            created_at=(
                base
                .replace(
                    minute=10,
                    second=5,
                )
                .isoformat()
            ),

            trading_account_id=(
                "account-1"
            ),

            currency="RUB",

            equity=Decimal(
                "100"
            ),
        ),

        BalanceSnapshot(
            created_at=(
                base
                .replace(
                    minute=10,
                    second=10,
                )
                .isoformat()
            ),

            trading_account_id=(
                "account-2"
            ),

            currency="RUB",

            equity=Decimal(
                "40"
            ),
        ),

        BalanceSnapshot(
            created_at=(
                base
                .replace(
                    minute=10,
                    second=20,
                )
                .isoformat()
            ),

            trading_account_id=(
                "account-1"
            ),

            currency="RUB",

            equity=Decimal(
                "110"
            ),
        ),

        BalanceSnapshot(
            created_at=(
                base
                .replace(
                    minute=40,
                )
                .isoformat()
            ),

            trading_account_id=(
                "account-1"
            ),

            currency="USDT",

            equity=Decimal(
                "50"
            ),
        ),
    ]

    monkeypatch\
        .setattr(
            api_module,

            "balance_snapshot_repository",

            FakeBalanceSnapshotRepository(
                snapshots,
            ),
        )

    def fake_dashboard():
        return {
            "total_equity": 190.0,

            "available_cash": 160.0,

            "invested_cash": 10.0,

            "available_cash_by_currency": {
                "RUB": 120.0,

                "USDT": 40.0,
            },

            "invested_cash_by_currency": {
                "RUB": 10.0,
            },
        }

    monkeypatch\
        .setattr(
            api_module,

            "dashboard",

            fake_dashboard,
        )

    client = (
        TestClient(
            app,
        )
    )

    response = (
        client
        .get(
            "/api/dashboard/history?days=7",
        )
    )

    assert (
        response
        .status_code
        == 200
    )

    data = (
        response
        .json()
    )

    assert (
        data[
            "equity_by_currency"
        ]
        == {
            "RUB": 130.0,

            "USDT": 40.0,
        }
    )

    assert (
        [
            point[
                "equity"
            ]

            for point
            in data[
                "points_by_currency"
            ][
                "RUB"
            ]
        ]
        == [
            150.0,

            130.0,
        ]
    )

    assert (
        [
            point[
                "equity"
            ]

            for point
            in data[
                "points_by_currency"
            ][
                "USDT"
            ]
        ]
        == [
            50.0,

            40.0,
        ]
    )

    assert (
        [
            point[
                "equity"
            ]

            for point
            in data[
                "points"
            ]
        ]
        == []
    )

    assert (
        "pnl_total"
        in data
    )


def test_dashboard_history_returns_points_by_account(
    monkeypatch,
) -> None:
    moment = (
        datetime
        .now(
            timezone.utc,
        )
    )

    base = (
        moment
        - timedelta(
            days=2,
        )
    )

    class FakeBalanceSnapshotRepository:
        def __init__(
            self,
            snapshots,
        ):
            self.snapshots = (
                snapshots
            )

        def get_since(
            self,
            since,
        ):
            return (
                self
                .snapshots
            )

    snapshots = [
        BalanceSnapshot(
            created_at=(
                base
                .replace(
                    minute=10,
                    second=5,
                )
                .isoformat()
            ),

            trading_account_id=(
                "account-1"
            ),

            currency="RUB",

            equity=Decimal(
                "100"
            ),
        ),

        BalanceSnapshot(
            created_at=(
                base
                .replace(
                    minute=10,
                    second=10,
                )
                .isoformat()
            ),

            trading_account_id=(
                "account-2"
            ),

            currency="RUB",

            equity=Decimal(
                "40"
            ),
        ),

        BalanceSnapshot(
            created_at=(
                base
                .replace(
                    minute=40,
                )
                .isoformat()
            ),

            trading_account_id=(
                "account-1"
            ),

            currency="RUB",

            equity=Decimal(
                "110"
            ),
        ),
    ]

    monkeypatch\
        .setattr(
            api_module,

            "balance_snapshot_repository",

            FakeBalanceSnapshotRepository(
                snapshots,
            ),
        )

    def fake_dashboard():
        return {
            "available_cash": 150.0,

            "invested_cash": 0.0,

            "available_cash_by_currency": {
                "RUB": 150.0,
            },

            "invested_cash_by_currency": {},
        }

    monkeypatch\
        .setattr(
            api_module,

            "dashboard",

            fake_dashboard,
        )

    client = (
        TestClient(
            app,
        )
    )

    response = (
        client
        .get(
            "/api/dashboard/history?days=7",
        )
    )

    assert (
        response
        .status_code
        == 200
    )

    data = (
        response
        .json()
    )

    points_by_account = (
        data[
            "points_by_account"
        ]
    )

    assert (
        set(
            points_by_account,
        )
        == {
            "account-1",

            "account-2",
        }
    )

    assert (
        [
            point[
                "equity"
            ]

            for point
            in points_by_account[
                "account-1"
            ]
        ]
        == [
            100.0,

            110.0,

            110.0,
        ]
    )

    assert (
        [
            point[
                "equity"
            ]

            for point
            in points_by_account[
                "account-2"
            ]
        ]
        == [
            40.0,

            40.0,
        ]
    )

    accounts = {
        item[
            "id"
        ]: item

        for item
        in data[
            "accounts"
        ]
    }

    assert (
        set(
            accounts,
        )
        == {
            "account-1",

            "account-2",
        }
    )

    assert (
        accounts[
            "account-1"
        ][
            "currency"
        ]
        == "RUB"
    )

    assert (
        accounts[
            "account-2"
        ][
            "currency"
        ]
        == "RUB"
    )


def test_dashboard_accounts_detail_uses_snapshots(
    monkeypatch,
) -> None:
    from domain.trading_account import (
        BrokerType,
        TradingAccount,
        TradingAccountMode,
    )

    moment = (
        datetime
        .now(
            timezone.utc,
        )
    )

    base = (
        moment
        - timedelta(
            days=1,
        )
    )

    accounts = [
        TradingAccount(
            id="account-1",

            name="РћСЃРЅРѕРІРЅРѕР№",

            broker=(
                BrokerType
                .TINVEST
            ),

            broker_account_id=(
                "100"
            ),

            mode=(
                TradingAccountMode
                .LIVE
            ),
        ),

        TradingAccount(
            id="account-2",

            name="Bybit",

            broker=(
                BrokerType
                .BYBIT
            ),

            broker_account_id=(
                "200"
            ),

            mode=(
                TradingAccountMode
                .LIVE
            ),

            base_currency=(
                "USDT"
            ),

            enabled=(
                False
            ),
        ),
    ]

    class FakeTradingAccountService:
        def get_all(
            self,
        ):
            return (
                accounts
            )

        def get_credentials(
            self,
            account_id,
        ):
            raise (
                RuntimeError(
                    "no credentials in test",
                )
            )

    class FakeBalanceSnapshotRepository:
        def __init__(
            self,
            snapshots,
        ):
            self.snapshots = (
                snapshots
            )

        def get_since(
            self,
            since,
        ):
            return (
                self
                .snapshots
            )

    class FakeEquityHistoryService:
        def pnl_today_by_account(
            self,
            current_equity_by_account=None,
            snapshots_by_account=None,
        ):
            return {
                "account-1": (
                    Decimal(
                        "5",
                    )
                ),
            }

    snapshots = [
        BalanceSnapshot(
            created_at=(
                base
                .replace(
                    minute=10,
                )
                .isoformat()
            ),

            trading_account_id=(
                "account-1"
            ),

            currency="RUB",

            equity=Decimal(
                "100"
            ),
        ),

        BalanceSnapshot(
            created_at=(
                base
                .replace(
                    minute=40,
                )
                .isoformat()
            ),

            trading_account_id=(
                "account-1"
            ),

            currency="RUB",

            equity=Decimal(
                "110"
            ),
        ),

        BalanceSnapshot(
            created_at=(
                base
                .replace(
                    minute=40,
                )
                .isoformat()
            ),

            trading_account_id=(
                "account-2"
            ),

            currency="USDT",

            equity=Decimal(
                "40"
            ),
        ),
    ]

    monkeypatch\
        .setattr(
            api_module,

            "trading_account_service",

            FakeTradingAccountService(),
        )

    monkeypatch\
        .setattr(
            api_module,

            "balance_snapshot_repository",

            FakeBalanceSnapshotRepository(
                snapshots,
            ),
        )

    monkeypatch\
        .setattr(
            api_module,

            "equity_history_service",

            FakeEquityHistoryService(),
        )

    client = (
        TestClient(
            app,
        )
    )

    response = (
        client
        .get(
            "/api/dashboard",
        )
    )

    assert (
        response
        .status_code
        == 200
    )

    detail_by_id = {
        item[
            "id"
        ]: item

        for item
        in (
            response
            .json()[
                "accounts_detail"
            ]
        )
    }

    assert (
        detail_by_id[
            "account-1"
        ][
            "name"
        ]
        == "РћСЃРЅРѕРІРЅРѕР№"
    )

    assert (
        detail_by_id[
            "account-1"
        ][
            "broker"
        ]
        == "tinvest"
    )

    assert (
        detail_by_id[
            "account-1"
        ][
            "mode"
        ]
        == "live"
    )

    assert (
        detail_by_id[
            "account-1"
        ][
            "currency"
        ]
        == "RUB"
    )

    assert (
        detail_by_id[
            "account-1"
        ][
            "balance"
        ]
        == 110.0
    )

    assert (
        detail_by_id[
            "account-1"
        ][
            "pnl_today"
        ]
        == 5.0
    )

    assert (
        detail_by_id[
            "account-2"
        ][
            "currency"
        ]
        == "USDT"
    )

    assert (
        detail_by_id[
            "account-2"
        ][
            "balance"
        ]
        == 40.0
    )

    assert (
        detail_by_id[
            "account-2"
        ][
            "pnl_today"
        ]
        is None
    )

    assert (
        detail_by_id[
            "account-2"
        ][
            "enabled"
        ]
        is False
    )


def test_instruments_endpoint_returns_instruments() -> None:
    client = TestClient(app)

    response = client.get(
        "/api/instruments"
    )

    assert response.status_code == 200

    data = response.json()

    assert (
        "instruments"
        in data
    )


    assert (
        data["instruments"]
        == []
    )


def test_start_sandbox_endpoint_starts_sessions() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/start-sandbox",
        json={
            "force": True,
            "instruments": [
                {
                    "ticker": "SBER",
                    "levels": 20,
                    "quantity": 1,
                }
            ],
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert (
        data["status"]
        == "started"
    )

    assert (
        data["mode"]
        == "sandbox"
    )

    assert (
        data["sessions"][0]["ticker"]
        == "SBER"
    )


def test_sessions_endpoint_returns_sessions() -> None:
    client = TestClient(app)

    client.post(
        "/api/start-sandbox",
        json={
            "force": False,
            "instruments": [
                {
                    "ticker": "GAZP",
                    "levels": 10,
                    "quantity": 1,
                }
            ],
        },
    )

    response = client.get(
        "/api/sessions"
    )

    assert response.status_code == 200

    data = response.json()

    tickers = {
        session["ticker"]
        for session in data["sessions"]
    }

    assert "GAZP" in tickers


def test_session_detail_endpoint_returns_session() -> None:
    client = TestClient(app)

    client.post(
        "/api/start-sandbox",
        json={
            "force": False,
            "instruments": [
                {
                    "ticker": "LKOH",
                    "levels": 20,
                    "quantity": 1,
                }
            ],
        },
    )

    response = client.get(
        "/api/session/LKOH"
    )

    assert response.status_code == 200

    data = response.json()

    assert (
        data["ticker"]
        == "LKOH"
    )

    assert (
        data["status"]
        == "ACTIVE"
    )

    assert (
        data["current_price"]
        == 4453
    )


def test_stop_session_endpoint_removes_session_when_positions_are_zero() -> None:
    client = TestClient(app)

    client.post(
        "/api/start-sandbox",
        json={
            "force": False,
            "instruments": [
                {
                    "ticker": "VTBR",
                    "levels": 20,
                    "quantity": 1,
                }
            ],
        },
    )

    response = client.post(
        "/api/stop-session/VTBR"
    )

    assert response.status_code == 200

    data = response.json()

    assert (
        data["ticker"]
        == "VTBR"
    )

    assert (
        data["status"]
        == "REMOVED"
    )

    assert (
        data["removed"]
        is True
    )

    sessions_response = client.get(
        "/api/sessions"
    )

    sessions_data = (
        sessions_response.json()
    )

    tickers = {
        session["ticker"]
        for session
        in sessions_data["sessions"]
    }

    assert "VTBR" not in tickers


def test_api_usage_endpoint_returns_summary() -> None:
    client = TestClient(app)

    response = client.get(
        "/api/api-usage"
    )

    assert response.status_code == 200

    data = response.json()

    assert "total_weight" in data
    assert "events_count" in data
    assert "by_operation" in data

    assert "last_1s_weight" in data
    assert "last_60s_weight" in data
    assert "last_300s_weight" in data

    assert (
        "active_sessions_count"
        in data
    )

    assert (
        "per_minute_per_session"
        in data
    )


@dataclass(slots=True)
class FakePosition:
    quantity: int


@dataclass(slots=True)
class FakeGridEngine:
    open_positions: dict[
        int,
        FakePosition,
    ] = field(
        default_factory=dict
    )

    realized_profit: Decimal = (
        Decimal("0")
    )


@dataclass(slots=True)
class FakeSandboxSession:
    current_price: Decimal
    grid_engine: FakeGridEngine

    unrealized_profit: Decimal = (
        Decimal("0")
    )


def test_session_endpoint_prefers_sandbox_snapshot() -> None:
    client = TestClient(app)

    client.post(
        "/api/start-sandbox",
        json={
            "force": False,
            "instruments": [
                {
                    "ticker": "SBER",
                    "levels": 20,
                    "quantity": 1,
                }
            ],
        },
    )

    sandbox_session_registry.register(
        ticker="SBER",
        session=FakeSandboxSession(
            current_price=Decimal(
                "333"
            ),
            grid_engine=FakeGridEngine(
                open_positions={
                    1: FakePosition(
                        quantity=10,
                    )
                },
                realized_profit=(
                    Decimal("12")
                ),
            ),
            unrealized_profit=(
                Decimal("5")
            ),
        ),
    )

    response = client.get(
        "/api/session/SBER"
    )

    assert response.status_code == 200

    data = response.json()

    assert (
        data["ticker"]
        == "SBER"
    )

    assert (
        data["current_price"]
        == 333.0
    )

    assert (
        data["positions"]
        == 1
    )

    assert (
        data["quantity"]
        == 10
    )

    assert (
        data["realized_profit"]
        == 12.0
    )

    assert (
        data["unrealized_profit"]
        == 5.0
    )

    assert (
        data["total_profit"]
        == 17.0
    )

    sandbox_session_registry.unregister(
        ticker="SBER",
    )


def test_runner_status_endpoint_returns_runners_list() -> None:
    client = TestClient(app)

    response = client.get(
        "/api/runner-status"
    )

    assert response.status_code == 200

    data = response.json()

    assert "runners" in data

    assert isinstance(
        data["runners"],
        list,
    )


def test_selected_tinvest_live_account_starts_without_legacy_environment_flags(monkeypatch):
    account = TradingAccount(id="selected-live", name="T-Invest", broker=BrokerType.TINVEST,
        broker_account_id="broker-live", mode=TradingAccountMode.LIVE)
    calls = []
    context = SimpleNamespace(account_id=account.broker_account_id)
    monkeypatch.setattr(settings, "trading_mode", "sandbox")
    monkeypatch.setattr(settings, "live_trading_enabled", False)
    monkeypatch.setattr(settings, "tinvest_token", None)
    monkeypatch.setattr(settings, "tinvest_live_account_id", None)
    monkeypatch.setattr(api_module, "trading_account_service", SimpleNamespace(
        get=lambda _: account, get_credentials=lambda _: SimpleNamespace(require=lambda _: "stored-token"),
    ))
    monkeypatch.setattr(api_module, "commission_service", SimpleNamespace(is_forced_drain=lambda: False))
    def validate(**kwargs):
        calls.append(("validate", kwargs["trading_account_id"]))
        return SimpleNamespace(total_required_deposit=Decimal("500"))
    monkeypatch.setattr(api_module, "live_start_validation_service", SimpleNamespace(validate=validate))
    class Factory:
        def __init__(self, **kwargs):
            pass
        def create_live_session_for_account(self, **kwargs):
            assert kwargs["token"] == "stored-token"
            assert kwargs["broker_account_id"] == account.broker_account_id
            calls.append(("create", kwargs["broker_account_id"]))
            return context
    monkeypatch.setattr(api_module, "MultiInstrumentTradingSessionFactory", Factory)
    monkeypatch.setattr(api_module, "WebRunnerService", lambda **kwargs: SimpleNamespace(**kwargs))
    monkeypatch.setattr(api_module, "web_runner_registry", SimpleNamespace(
        has_session_id=lambda _: False, start=lambda runner: calls.append(("start", runner.trading_account_id)),
        ensure_instruments_available=lambda *args: None,
    ))
    monkeypatch.setattr(api_module, "session_registry", SimpleNamespace(start_session=lambda **kwargs: SimpleNamespace(**kwargs)))
    monkeypatch.setattr(api_module, "_build_display_session", lambda web_session: {"ticker": web_session.ticker})
    response = TestClient(app).post("/api/start-live", json={
        "trading_account_id": account.id, "instruments": [{"ticker": "SBER", "levels": 5, "quantity": 1}],
    })
    assert response.status_code == 200, response.text
    assert response.json()["trading_account_id"] == account.id
    assert calls == [("validate", account.id), ("create", account.broker_account_id), ("start", account.id)]


def test_start_live_rejects_partial_overlap_before_validation_or_broker_access(monkeypatch):
    from application.web_runner_registry import WebRunnerRegistry

    registry = WebRunnerRegistry()
    existing = SimpleNamespace(
        session_id="first", trading_account_id="selected-live", is_running=True,
        context=SimpleNamespace(instrument_ids_by_ticker={"SMLT": "smlt-uid", "SBER": "sber-uid"}),
    )
    registry.register(existing)
    monkeypatch.setattr(api_module, "web_runner_registry", registry)
    monkeypatch.setattr(api_module, "trading_account_service", SimpleNamespace(
        get=lambda _: pytest.fail("Overlap must be rejected before loading account or credentials"),
    ))
    monkeypatch.setattr(api_module, "live_start_validation_service", SimpleNamespace(
        validate=lambda **kwargs: pytest.fail("Overlap must be rejected before broker validation"),
    ))
    response = TestClient(app).post("/api/start-live", json={
        "trading_account_id": "selected-live", "instruments": [
            {"ticker": "smlt", "levels": 5, "quantity": 1},
            {"ticker": "GAZP", "levels": 5, "quantity": 1},
            {"ticker": "LKOH", "levels": 5, "quantity": 1},
        ],
    })
    assert response.status_code == 409
    assert "SMLT" in response.json()["detail"]
    assert registry.get_all() == [existing]


def test_start_live_is_blocked_when_live_disabled(
    monkeypatch,
) -> None:
    client = TestClient(app)

    monkeypatch.setattr(
        settings,
        "trading_mode",
        "live",
    )

    monkeypatch.setattr(
        settings,
        "live_trading_enabled",
        False,
    )

    monkeypatch.setattr(
        settings,
        "tinvest_token",
        "test-token",
    )

    monkeypatch.setattr(
        settings,
        "tinvest_live_account_id",
        "test-account",
    )

    response = client.post(
        "/api/start-live",
        json={
            "force": False,
            "instruments": [
                {
                    "ticker": "SBER",
                    "levels": 20,
                    "quantity": 1,
                }
            ],
        },
    )

    assert (
        response.status_code
        == 403
    )

    data = response.json()

    assert (
        "LIVE_TRADING_ENABLED"
        in data["detail"]
    )


def test_start_live_is_blocked_in_sandbox_mode(
    monkeypatch,
) -> None:
    client = TestClient(app)

    monkeypatch.setattr(
        settings,
        "trading_mode",
        "sandbox",
    )

    monkeypatch.setattr(
        settings,
        "live_trading_enabled",
        True,
    )

    monkeypatch.setattr(
        settings,
        "tinvest_token",
        "test-token",
    )

    monkeypatch.setattr(
        settings,
        "tinvest_live_account_id",
        "test-account",
    )

    response = client.post(
        "/api/start-live",
        json={
            "force": False,
            "instruments": [
                {
                    "ticker": "SBER",
                    "levels": 20,
                    "quantity": 1,
                }
            ],
        },
    )

    assert (
        response.status_code
        == 403
    )

    data = response.json()

    assert (
        "TRADING_MODE"
        in data["detail"]
    )


def test_format_money_rounds_half_up() -> None:
    assert (
        api_module
        ._format_money(
            Decimal("10.005")
        )
        == "10.01"
    )


def test_format_money_keeps_two_decimals() -> None:
    assert (
        api_module
        ._format_money(
            Decimal("5.1")
        )
        == "5.10"
    )


def test_format_money_zero_and_integers() -> None:
    assert (
        api_module
        ._format_money(
            Decimal("0")
        )
        == "0.00"
    )

    assert (
        api_module
        ._format_money(
            Decimal("7")
        )
        == "7.00"
    )


def test_format_money_rounds_long_fractions() -> None:
    assert (
        api_module
        ._format_money(
            Decimal("123.456")
        )
        == "123.46"
    )

    assert (
        api_module
        ._format_money(
            Decimal("1000000.999")
        )
        == "1000001.00"
    )


class _FakeHeadClient:
    def __init__(self) -> None:
        self.calls = []

    def confirm_password_reset(
        self,
        login,
        code,
        new_password_hash,
    ):
        self.calls.append(
            (
                login,
                code,
                new_password_hash,
            )
        )

        if code != "654321":
            return (
                None,

                "РќРµРІРµСЂРЅС‹Р№ РєРѕРґ "
                "СЃР±СЂРѕСЃР°",
            )

        return (
            "fake-api-key",

            None,
        )


def test_password_reset_endpoint_flow(
    monkeypatch,
) -> None:
    client = TestClient(app)

    fake_head = _FakeHeadClient()

    monkeypatch.setattr(
        api_module,
        "head_server_client",
        fake_head,
    )

    register = client.post(
        "/api/auth/register",

        json={
            "full_name": (
                "РџС‘С‚СЂ РЎР±СЂРѕСЃРѕРІ"
            ),

            "phone": (
                "+79001112233"
            ),

            "email": (
                "reset@example.com"
            ),

            "birth_date": (
                "1990-05-05"
            ),

            "login": (
                "resetapi"
            ),

            "password": (
                "oldpass"
            ),

            "device_id": (
                "web"
            ),
        },
    )

    assert (
        register
        .status_code
        == 200
    )

    wrong_code = client.post(
        "/api/auth/password/reset",

        json={
            "login": (
                "resetapi"
            ),

            "code": (
                "111111"
            ),

            "password": (
                "newpass"
            ),

            "device_id": (
                "web"
            ),
        },
    )

    assert (
        wrong_code
        .status_code
        == 400
    )

    old_login = client.post(
        "/api/auth/login",

        json={
            "login": (
                "resetapi"
            ),

            "password": (
                "oldpass"
            ),

            "device_id": (
                "web"
            ),
        },
    )

    assert (
        old_login
        .status_code
        == 200
    )

    confirm = client.post(
        "/api/auth/password/reset",

        json={
            "login": (
                "resetapi"
            ),

            "code": (
                "654321"
            ),

            "password": (
                "newpass"
            ),

            "device_id": (
                "web"
            ),
        },
    )

    assert (
        confirm
        .status_code
        == 200
    )

    assert (
        confirm
        .json()["user"][
            "login"
        ]
        == "resetapi"
    )

    assert (
        "esm_auth" in (
            confirm
            .cookies
        )
    )

    assert (
        fake_head
        .calls
    )

    login_arg, code_arg, hash_arg = (
        fake_head
        .calls[-1]
    )

    assert (
        login_arg
        == "resetapi"
    )

    assert (
        "$" in hash_arg
    )

    stale_login = client.post(
        "/api/auth/login",

        json={
            "login": (
                "resetapi"
            ),

            "password": (
                "oldpass"
            ),

            "device_id": (
                "web"
            ),
        },
    )

    assert (
        stale_login
        .status_code
        == 401
    )

    fresh_login = client.post(
        "/api/auth/login",

        json={
            "login": (
                "resetapi"
            ),

            "password": (
                "newpass"
            ),

            "device_id": (
                "web"
            ),
        },
    )

    assert (
        fresh_login
        .status_code
        == 200
    )


def test_password_reset_requires_head_server(
    monkeypatch,
) -> None:
    client = TestClient(app)

    monkeypatch.setattr(
        api_module,
        "head_server_client",
        None,
    )

    response = client.post(
        "/api/auth/password/reset",

        json={
            "login": (
                "anyone"
            ),

            "code": (
                "654321"
            ),

            "password": (
                "newpass"
            ),

            "device_id": (
                "web"
            ),
        },
    )

    assert (
        response
        .status_code
        == 503
    )


def test_password_reset_unknown_local_user(
    monkeypatch,
) -> None:
    client = TestClient(app)

    monkeypatch.setattr(
        api_module,
        "head_server_client",
        _FakeHeadClient(),
    )

    response = client.post(
        "/api/auth/password/reset",

        json={
            "login": (
                "ghost-user"
            ),

            "code": (
                "654321"
            ),

            "password": (
                "newpass"
            ),

            "device_id": (
                "web"
            ),
        },
    )

    assert (
        response
        .status_code
        == 404
    )



def test_accounts_overview_structure(
    monkeypatch,
) -> None:
    moment = (
        datetime
        .now(
            timezone.utc,
        )
    )

    base = (
        moment
        - timedelta(
            days=1,
        )
    )

    accounts = [
        TradingAccount(
            id="account-1",

            name="РћСЃРЅРѕРІРЅРѕР№",

            broker=(
                BrokerType
                .TINVEST
            ),

            broker_account_id=(
                "100"
            ),

            mode=(
                TradingAccountMode
                .LIVE
            ),
        ),
    ]

    class FakeTradingAccountService:
        def get_all(
            self,
        ):
            return (
                accounts
            )

        def get_credentials(
            self,
            account_id,
        ):
            raise (
                RuntimeError(
                    "no credentials in test",
                )
            )

    class FakeBalanceSnapshotRepository:
        def __init__(
            self,
            snapshots,
        ):
            self.snapshots = (
                snapshots
            )

        def get_since(
            self,
            since,
        ):
            return (
                self
                .snapshots
            )

    class FakeEquityHistoryService:
        def snapshot_points(
            self,
            snapshots,
            now,
        ):
            points = [
                {
                    "ts": (
                        ts
                        .isoformat()
                    ),

                    "equity": float(
                        value
                    ),
                }

                for ts, value
                in snapshots
            ]

            points.append(
                {
                    "ts": (
                        now
                        .isoformat()
                    ),

                    "equity": float(
                        snapshots[
                            -1
                        ][
                            1
                        ]
                    ),
                }
            )

            return points

    class FakeStateRepository:
        def get_all(
            self,
        ):
            state = (
                SimpleNamespace(
                    trading_account_id=(
                        "account-1"
                    ),
                    status="RUNNING",

                    available_cash=(
                        Decimal(
                            "70",
                        )
                    ),

                    reserved_cash=(
                        Decimal(
                            "10",
                        )
                    ),

                    instruments=[
                        SimpleNamespace(
                            ticker=(
                                "SBER"
                            ),

                            instrument_uid=(
                                "uid-sber"
                            ),
                            cycle_closed_orders=2,
                            cycle_realized_profit=Decimal("3"),
                            grid_config=None,
                            current_price=None,
                            grid_step=None,
                            session_start_price=None,

                            levels=[
                                SimpleNamespace(
                                    level_index=(
                                        1
                                    ),

                                    level_price=(
                                        Decimal(
                                            "100",
                                        )
                                    ),

                                    status=(
                                        GridLevelStatus
                                        .WAITING_PRICE
                                    ),
                                ),
                            ],

                            open_positions=[
                                SimpleNamespace(
                                    level_index=(
                                        0
                                    ),

                                    entry_price=(
                                        Decimal(
                                            "98",
                                        )
                                    ),

                                    quantity=(
                                        2
                                    ),

                                    purchase_cost=(
                                        Decimal(
                                            "196",
                                        )
                                    ),

                                    hard_take_profit_price=Decimal("100"),
                                    trailing_exit_target_price=(
                                        None
                                    ),
                                ),
                            ],
                        ),
                    ],
                )
            )

            return [
                state,
            ]

    class FakeRunnerRegistry:
        def get_all(
            self,
        ):
            return []

    class FakeBrokerRegistry:
        def get(
            self,
            broker,
        ):
            raise (
                RuntimeError(
                    "no broker in test",
                )
            )

    snapshots = [
        BalanceSnapshot(
            created_at=(
                base
                .replace(
                    minute=10,
                )
                .isoformat()
            ),

            trading_account_id=(
                "account-1"
            ),

            currency="RUB",

            equity=Decimal(
                "100"
            ),
        ),

        BalanceSnapshot(
            created_at=(
                base
                .replace(
                    minute=40,
                )
                .isoformat()
            ),

            trading_account_id=(
                "account-1"
            ),

            currency="RUB",

            equity=Decimal(
                "110"
            ),
        ),
    ]

    monkeypatch\
        .setattr(
            api_module,

            "trading_account_service",

            FakeTradingAccountService(),
        )

    monkeypatch\
        .setattr(
            api_module,

            "balance_snapshot_repository",

            FakeBalanceSnapshotRepository(
                snapshots,
            ),
        )

    monkeypatch\
        .setattr(
            api_module,

            "equity_history_service",

            FakeEquityHistoryService(),
        )

    monkeypatch\
        .setattr(
            api_module,

            "trading_state_repository",

            FakeStateRepository(),
        )

    monkeypatch\
        .setattr(
            api_module,

            "web_runner_registry",

            FakeRunnerRegistry(),
        )

    monkeypatch\
        .setattr(
            api_module,

            "broker_registry",

            FakeBrokerRegistry(),
        )

    monkeypatch\
        .setattr(
            api_module,

            "_resolve_chart_token",

            lambda state: (
                "test-token"
            ),
        )

    monkeypatch\
        .setattr(
            api_module,

            "_overview_change_24h",

            lambda token, instrument_uid: (
                (
                    2.0,

                    1.0,
                )
            ),
        )

    client = (
        TestClient(
            app,
        )
    )

    response = (
        client
        .get(
            "/api/overview",
        )
    )

    assert (
        response
        .status_code
        == 200
    )

    data = (
        response
        .json()
    )

    assert (
        len(
            data[
                "accounts"
            ]
        )
        == 1
    )

    account = (
        data[
            "accounts"
        ][
            0
        ]
    )

    assert (
        account[
            "id"
        ]
        == (
            "account-1"
        )
    )

    assert (
        account[
            "equity"
        ]
        == 110.0
    )

    assert (
        account[
            "available"
        ]
        == 70.0
    )

    assert (
        account[
            "invested"
        ]
        == 196.0
    )

    assert (
        account[
            "reserved"
        ]
        == 10.0
    )

    assert (
        len(
            account[
                "balance_series"
            ]
        )
        == 3
    )

    tickers = [
        asset[
            "ticker"
        ]

        for asset
        in (
            account[
                "assets"
            ]
        )
    ]

    assert (
        tickers
        == [
            "RUB",

            "SBER",
        ]
    )

    sber = (
        account[
            "assets"
        ][
            1
        ]
    )

    assert (
        sber[
            "quantity"
        ]
        == 2.0
    )

    assert (
        sber[
            "change_24h"
        ]
        == 2.0
    )

    assert (
        len(
            account[
                "sessions"
            ]
        )
        == 1
    )

    session = (
        account[
            "sessions"
        ][
            0
        ]
    )

    assert session["closed_orders"] == 2
    assert session["cycle_profit"] == 3.0
    assert session["pnl_percent"] > 0
    assert session["next_buy_activation"] == 100.0
    assert session["next_sell_activation"] > 100.0

    state = FakeStateRepository().get_all()[0]
    position = state.instruments[0].open_positions[0]
    position.purchase_cost = Decimal("1960")
    position.buy_commission = Decimal("0")
    state.instruments[0].current_price = Decimal("100")
    monkeypatch.setattr(api_module, "trading_state_repository", SimpleNamespace(get_all=lambda: [state]))
    monkeypatch.setattr(api_module, "trading_account_service", SimpleNamespace(
        get_all=lambda: accounts, get_credentials=lambda account_id: SimpleNamespace(values={}),
    ))
    monkeypatch.setattr(api_module, "broker_registry", SimpleNamespace(get=lambda broker: SimpleNamespace(
        get_portfolio=lambda **kwargs: SimpleNamespace(cash=Decimal("70"), total_value=Decimal("10000")),
    )))
    live_account = client.get("/api/overview").json()["accounts"][0]
    assert live_account["equity"] == 10000.0
    assert live_account["invested"] == 2000.0
    assert live_account["assets"][1]["value"] == 2000.0
    assert live_account["reserved"] == 10.0

    assert (
        session[
            "ticker"
        ]
        == (
            "SBER"
        )
    )

    assert (
        len(
            session[
                "orders_bought"
            ]
        )
        == 1
    )

    assert (
        session[
            "orders_bought"
        ][
            0
        ][
            "price"
        ]
        == (
            "98"
        )
    )

    assert (
        len(
            session[
                "orders_planned"
            ]
        )
        == 1
    )

    assert (
        session[
            "orders_planned"
        ][
            0
        ][
            "status"
        ]
        == (
            "WAITING_PRICE"
        )
    )


def test_session_chart_starts_at_current_session_and_defaults_to_fifteen_minutes(monkeypatch):
    now = datetime.now(timezone.utc)
    started = now - timedelta(hours=3)
    instrument = SimpleNamespace(ticker="SBER", instrument_uid="asset", levels=[], open_positions=[])
    state = SimpleNamespace(session_id="current", trading_account_id="account-1", started_at=started.isoformat(), instruments=[instrument])
    calls = []

    class History:
        def __init__(self, **kwargs):
            pass

        def get_candles(self, **kwargs):
            calls.append(kwargs)
            return [Candle("asset", Decimal("100"), Decimal("101"), Decimal("99"), Decimal("100"), 1, timestamp)
                    for timestamp in (started - timedelta(hours=1), started + timedelta(minutes=15), now)]

    events = [OperationEvent(timestamp.isoformat(), "BUY", account, "asset", "SBER", "цена=100")
              for timestamp, account in [(started - timedelta(days=1), "account-1"), (now, "account-2"), (now, "account-1")]]
    monkeypatch.setattr(api_module, "trading_state_repository", SimpleNamespace(get_all=lambda: [state]))
    monkeypatch.setattr(api_module, "TInvestHistoryProvider", History)
    monkeypatch.setattr(api_module, "_resolve_chart_token", lambda state: "fake")
    monkeypatch.setattr(api_module, "operation_log_repository", SimpleNamespace(get_since=lambda **kwargs: events))
    result = api_module.session_chart("SBER")
    assert result["interval"] == "15m"
    assert result["started_at"] == started.isoformat()
    assert calls[0]["date_from"] == started
    assert len(result["candles"]) == 2
    assert len(result["trades"]) == 1


def test_session_chart_interval_passthrough(
    monkeypatch,
) -> None:
    calls = []

    class FakeHistoryProvider:
        def __init__(
            self,
            client_factory,
            mapper,
        ):
            pass

        def get_candles(
            self,
            instrument_id,
            date_from,
            date_to,
            interval,
        ):
            calls.append(
                {
                    "instrument_id": (
                        instrument_id
                    ),

                    "days": (
                        (
                            date_to
                            - date_from
                        )
                        .days
                    ),

                    "interval": (
                        interval
                    ),
                }
            )

            now = (
                datetime
                .now(
                    timezone.utc,
                )
            )

            return [
                Candle(
                    instrument_id=(
                        instrument_id
                    ),

                    open=(
                        Decimal(
                            "100",
                        )
                    ),

                    high=(
                        Decimal(
                            "101",
                        )
                    ),

                    low=(
                        Decimal(
                            "99",
                        )
                    ),

                    close=(
                        Decimal(
                            "100",
                        )
                    ),

                    volume=10,

                    timestamp=(
                        now
                        - timedelta(
                            days=1,
                        )
                    ),
                ),

                Candle(
                    instrument_id=(
                        instrument_id
                    ),

                    open=(
                        Decimal(
                            "100",
                        )
                    ),

                    high=(
                        Decimal(
                            "102",
                        )
                    ),

                    low=(
                        Decimal(
                            "99",
                        )
                    ),

                    close=(
                        Decimal(
                            "101",
                        )
                    ),

                    volume=10,

                    timestamp=(
                        now
                    ),
                ),
            ]

    state = (
        SimpleNamespace(
            session_id=(
                "session-1"
            ),

            trading_account_id=(
                None
            ),

            instruments=[
                SimpleNamespace(
                    ticker=(
                        "sber"
                    ),

                    instrument_uid=(
                        "uid-sber"
                    ),

                    levels=[],

                    open_positions=[],
                ),
            ],
        )
    )

    class FakeStateRepository:
        def get_all(
            self,
        ):
            return [
                state,
            ]

    monkeypatch\
        .setattr(
            api_module,

            "trading_state_repository",

            FakeStateRepository(),
        )

    monkeypatch\
        .setattr(
            api_module,

            "TInvestHistoryProvider",

            FakeHistoryProvider,
        )

    monkeypatch\
        .setattr(
            api_module,

            "_resolve_chart_token",

            lambda raw_state: (
                "test-token"
            ),
        )

    client = (
        TestClient(
            app,
        )
    )

    response = (
        client
        .get(
            "/api/session/SBER/chart"
            "?days=90&interval=1h",
        )
    )

    assert (
        response
        .status_code
        == 200
    )

    data = (
        response
        .json()
    )

    assert (
        data[
            "interval"
        ]
        == (
            "1h"
        )
    )

    assert (
        calls[
            -1
        ][
            "interval"
        ]
        == (
            "1h"
        )
    )

    assert (
        calls[
            -1
        ][
            "days"
        ]
        == 30
    )

    fallback = (
        client
        .get(
            "/api/session/SBER/chart"
            "?days=90&interval=9h",
        )
    )

    assert (
        fallback
        .status_code
        == 200
    )

    assert (
        fallback
        .json()[
            "interval"
        ]
        == (
            "1d"
        )
    )

    assert (
        calls[
            -1
        ][
            "days"
        ]
        == 90
    )


def test_auth_profile_update_flow(
    monkeypatch,
) -> None:
    stored = (
        api_module
        .user_repository
        .create_user(
            full_name=(
                "РЎС‚Р°СЂРѕРµ РРјСЏ"
            ),

            phone=(
                "+70000000000"
            ),

            email=(
                "old@example.com"
            ),

            birth_date=(
                "1990-01-01"
            ),

            login=(
                "profileuser"
            ),

            password_hash=(
                "salt$digest"
            ),
        )
    )

    fake_user = (
        SimpleNamespace(
            id=(
                stored
                .id
            ),

            login=(
                "profileuser"
            ),

            full_name=(
                stored
                .full_name
            ),
        )
    )

    monkeypatch\
        .setattr(
            api_module,

            "_auth_user",

            lambda request: (
                fake_user,

                "token",
            ),
        )

    client = (
        TestClient(
            app,
        )
    )

    response = (
        client
        .patch(
            "/api/auth/profile",

            json={
                "full_name": (
                    "РќРѕРІРѕРµ РРјСЏ"
                ),

                "phone": (
                    "+79998887766"
                ),
            },
        )
    )

    assert (
        response
        .status_code
        == 200
    )

    data = (
        response
        .json()[
            "user"
        ]
    )

    assert (
        data[
            "full_name"
        ]
        == (
            "РќРѕРІРѕРµ РРјСЏ"
        )
    )

    assert (
        data[
            "phone"
        ]
        == (
            "+79998887766"
        )
    )

    updated = (
        api_module
        .user_repository
        .get_user_by_id(
            stored
            .id
        )
    )

    assert (
        updated
        .full_name
        == (
            "РќРѕРІРѕРµ РРјСЏ"
        )
    )

    assert (
        updated
        .email
        == (
            "old@example.com"
        )
    )

    me = (
        client
        .get(
            "/api/auth/me",
        )
    )

    assert (
        me
        .status_code
        == 200
    )

    me_user = (
        me
        .json()[
            "user"
        ]
    )

    assert (
        me_user[
            "email"
        ]
        == (
            "old@example.com"
        )
    )

    assert (
        me_user[
            "birth_date"
        ]
        == (
            "1990-01-01"
        )
    )

    empty_name = (
        client
        .patch(
            "/api/auth/profile",

            json={
                "full_name": (
                    "   "
                ),
            },
        )
    )

    assert (
        empty_name
        .status_code
        == 400
    )


def test_user_head_history_unavailable(
    monkeypatch,
) -> None:
    fake_user = (
        SimpleNamespace(
            id=(
                1
            ),

            login=(
                "user"
            ),

            full_name=(
                "РРјСЏ"
            ),
        )
    )

    monkeypatch\
        .setattr(
            api_module,

            "_auth_user",

            lambda request: (
                fake_user,

                "token",
            ),
        )

    monkeypatch\
        .setattr(
            api_module,

            "head_server_client",

            None,
        )

    client = (
        TestClient(
            app,
        )
    )

    response = (
        client
        .get(
            "/api/user/head-history",
        )
    )

    assert (
        response
        .status_code
        == 200
    )

    assert (
        response
        .json()[
            "available"
        ]
        is False
    )


def test_broker_sync_backfills_existing_accounts_and_retries_without_duplicates(monkeypatch, tmp_path):
    from domain.broker_operation import BrokerOperation
    from infrastructure.sqlite.broker_cash_flow_repository import SQLiteBrokerCashFlowRepository
    from infrastructure.sqlite.sqlite_database import SQLiteDatabase

    database = SQLiteDatabase(tmp_path / "sync.db")
    database.initialize()
    repository = SQLiteBrokerCashFlowRepository(database)
    monkeypatch.setattr(api_module, "broker_cash_flow_repository", repository)
    now = datetime.now(timezone.utc)
    account = SimpleNamespace(id="account-1", broker_account_id="broker-1", mode="live")
    repository.record(BrokerCashFlow(account.id, now.isoformat(), "input", "RUB", Decimal("10")))
    calls = []

    def get_operations(**kwargs):
        calls.append(kwargs)
        return [BrokerOperation(now - timedelta(days=120), "buy", Decimal("-10"), "USD", "buy-1")]

    adapter = SimpleNamespace(get_operations=get_operations)
    api_module._broker_cash_flows_sync(account, adapter, {}, "RUB")
    assert timedelta(days=180) <= datetime.now(timezone.utc) - calls[0]["since"] < timedelta(days=181)
    assert calls[0]["currency"] is None
    api_module._broker_cash_flows_sync(account, adapter, {}, "RUB")
    assert len(calls) == 1
    assert len(repository.operations_since("2000-01-01")) == 1
    assert len(repository.get_since("2000-01-01")) == 1


def test_operations_feed_includes_all_broker_operations_and_local_entries(monkeypatch, tmp_path):
    from domain.broker_operation import BrokerOperation
    from infrastructure.sqlite.broker_cash_flow_repository import SQLiteBrokerCashFlowRepository
    from infrastructure.sqlite.sqlite_database import SQLiteDatabase

    database = SQLiteDatabase(tmp_path / "feed.db")
    database.initialize()
    repository = SQLiteBrokerCashFlowRepository(database)
    now = datetime.now(timezone.utc)
    for index in range(120):
        repository.record_operation("account-1", BrokerOperation(
            now - timedelta(days=2), "buy", Decimal("-10"), "RUB", str(index),
        ))
    repository.record_operation("account-1", BrokerOperation(
        now - timedelta(days=181), "sell", Decimal("20"), "RUB", "old",
    ))
    monkeypatch.setattr(api_module, "broker_cash_flow_repository", repository)
    monkeypatch.setattr(api_module, "operation_log_repository", SimpleNamespace(
        recent=lambda limit: [OperationEvent(now.isoformat(), "POSITION_CLEARED", None, None, None, "local")],
    ))
    monkeypatch.setattr(api_module, "commission_repository", SimpleNamespace(recent=lambda limit: []))
    monkeypatch.setattr(api_module, "trading_account_service", SimpleNamespace(get_all=lambda: [
        SimpleNamespace(id="account-1", broker=BrokerType.TINVEST),
    ]))
    result = api_module.operations()["operations"]
    assert all(item["broker"] == "tinvest" for item in result[1:])
    assert result[0]["broker"] is None
    assert len(result) == 121
    assert result[0]["details"] == "local"
    assert all(item["event_type"] == "BUY" for item in result[1:])


def test_tinvest_operations_fetch_every_cursor_page():
    from contextlib import nullcontext
    from infrastructure.brokers.tinvest.adapter import TInvestBrokerAdapter

    calls = []

    def get_operations_by_cursor(request):
        calls.append(request)
        return SimpleNamespace(
            items=[request.cursor or "first"],
            has_next=not request.cursor,
            next_cursor="second",
        )

    factory = SimpleNamespace(create_live_client=lambda: nullcontext(SimpleNamespace(
        operations=SimpleNamespace(get_operations_by_cursor=get_operations_by_cursor),
    )))
    now = datetime.now(timezone.utc)
    result = TInvestBrokerAdapter()._get_live_operations(factory, "broker-1", now - timedelta(days=1), now)
    assert result == ["first", "second"]
    assert len(calls) == 2
    assert calls[0].without_commissions is False
    assert calls[0].without_trades is False


def test_tinvest_cursor_operation_type_and_payment_currency():
    from infrastructure.brokers.tinvest.adapter import TInvestBrokerAdapter
    from t_tech.invest.schemas import OperationType
    from t_tech.invest.grpc.operations import OperationState

    raw = SimpleNamespace(
        id="buy-1", date=datetime.now(timezone.utc),
        state=OperationState.OPERATION_STATE_EXECUTED,
        type=OperationType.OPERATION_TYPE_BUY,
        payment=SimpleNamespace(units=-10, nano=0, currency="rub"),
        instrument_uid="instrument-1", quantity=1,
    )
    parsed = TInvestBrokerAdapter._parse_operations([raw], None)
    assert parsed[0].kind == "buy"
    assert parsed[0].currency == "RUB"


def test_tinvest_operations_keep_ids_and_zero_payment_security_transfers():
    from infrastructure.brokers.tinvest.adapter import TInvestBrokerAdapter
    from t_tech.invest.schemas import OperationType
    from t_tech.invest.grpc.operations import OperationState

    raw = SimpleNamespace(
        id="transfer-1", date=datetime.now(timezone.utc), currency="RUB",
        state=OperationState.OPERATION_STATE_EXECUTED,
        operation_type=OperationType.OPERATION_TYPE_INPUT_SECURITIES,
        type="ignored", payment=SimpleNamespace(units=0, nano=0),
        instrument_uid="instrument-1", quantity=10,
    )
    parsed = TInvestBrokerAdapter._parse_operations([raw, raw], None)
    assert len(parsed) == 1
    assert parsed[0].kind == "inputsecurities"
    assert parsed[0].operation_id == "transfer-1"
    assert parsed[0].instrument_id == "instrument-1"
    assert parsed[0].quantity == Decimal("10")


def test_operations_endpoint_merges_flows_and_commissions(
    monkeypatch,
) -> None:
    class FakeOperationLogRepository:
        def recent(
            self,
            limit,
        ):
            return [
                OperationEvent(
                    created_at="2026-09-29T10:00:00+00:00",

                    event_type="SELL",

                    trading_account_id="account-1",

                    instrument_id="instrument-1",

                    ticker="ABC",

                    details="прибыль=5 ₽",
                ),

                OperationEvent(
                    created_at="2026-09-30T09:00:00+00:00",

                    event_type="TRAILING",

                    trading_account_id="account-1",

                    instrument_id="instrument-1",

                    ticker="ABC",

                    details="тралл",
                ),
            ]

    class FakeBrokerCashFlowRepository:
        def operations_since(self, since):
            return []

        def get_since(
            self,
            since,
        ):
            return [
                BrokerCashFlow(
                    trading_account_id="account-1",

                    occurred_at="2026-09-30T08:00:00+00:00",

                    kind="input",

                    currency="RUB",

                    payment=Decimal(
                        "50"
                    ),
                ),

                BrokerCashFlow(
                    trading_account_id="account-1",

                    occurred_at="2026-09-28T07:00:00+00:00",

                    kind="output",

                    currency="RUB",

                    payment=Decimal(
                        "-30"
                    ),
                ),
            ]

    class FakeCommissionRepository:
        def recent(
            self,
            limit,
        ):
            return [
                CommissionCharge(
                    id=1,

                    created_at="2026-09-30T12:00:00+00:00",

                    trading_account_id="account-1",

                    broker="tinvest",

                    instrument_id="instrument-1",

                    ticker="ABC",

                    level_index=1,

                    trade_profit=Decimal(
                        "10"
                    ),

                    percent=Decimal(
                        "10"
                    ),

                    amount=Decimal(
                        "1"
                    ),

                    balance_after=Decimal(
                        "99"
                    ),

                    synced_with_head=True,
                ),
            ]

    monkeypatch\
        .setattr(
            api_module,

            "operation_log_repository",

            FakeOperationLogRepository(),
        )

    monkeypatch\
        .setattr(
            api_module,

            "broker_cash_flow_repository",

            FakeBrokerCashFlowRepository(),
        )

    monkeypatch\
        .setattr(
            api_module,

            "commission_repository",

            FakeCommissionRepository(),
        )

    client = (
        TestClient(
            app,
        )
    )

    response = (
        client
        .get(
            "/api/operations?limit=10",
        )
    )

    assert (
        response
        .status_code
        == 200
    )

    data = (
        response
        .json()
    )

    pairs = [
        (
            item[
                "event_type"
            ],

            item[
                "created_at"
            ],
        )

        for item
        in data[
            "operations"
        ]
    ]

    assert (
        pairs
        == [
            (
                "COMMISSION",

                "2026-09-30T12:00:00+00:00",
            ),

            (
                "DEPOSIT",

                "2026-09-30T08:00:00+00:00",
            ),

            (
                "SELL",

                "2026-09-29T10:00:00+00:00",
            ),

            (
                "WITHDRAWAL",

                "2026-09-28T07:00:00+00:00",
            ),
        ]
    )

    assert (
        data[
            "operations"
        ][
            1
        ][
            "details"
        ]
        == "пополнение 50 RUB"
    )

    assert (
        data[
            "operations"
        ][
            3
        ][
            "details"
        ]
        == "вывод 30 RUB"
    )

    assert (
        "списание комиссии ЛК −1 ₽"
        in data[
            "operations"
        ][
            0
        ][
            "details"
        ]
    )

    limited = (
        client
        .get(
            "/api/operations?limit=2",
        )
        .json()
    )

    assert (
        len(
            limited[
                "operations"
            ]
        )
        == 2
    )

    assert (
        limited[
            "operations"
        ][
            0
        ][
            "event_type"
        ]
        == "COMMISSION"
    )
