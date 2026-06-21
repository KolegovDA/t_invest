from fastapi.testclient import TestClient

from web.api import app, session_registry
from application.sandbox_session_registry import (
    sandbox_session_registry,
)


def setup_function() -> None:
    session_registry.sessions.clear()
    sandbox_session_registry.sessions.clear()

def test_health_endpoint_returns_ok() -> None:
    client = TestClient(app)

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
    }


def test_version_endpoint_returns_version() -> None:
    client = TestClient(app)

    response = client.get("/api/version")

    assert response.status_code == 200
    assert response.json()["version"] == "1.0.0-mvp"


def test_dashboard_endpoint_returns_dashboard() -> None:
    client = TestClient(app)

    response = client.get("/api/dashboard")

    assert response.status_code == 200
    assert response.json()["accounts"] == 1


def test_instruments_endpoint_returns_instruments() -> None:
    client = TestClient(app)

    response = client.get("/api/instruments")

    assert response.status_code == 200

    data = response.json()

    assert len(data["instruments"]) == 3
    assert data["instruments"][0]["ticker"] == "SBER"


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

    assert data["status"] == "started"
    assert data["mode"] == "sandbox"
    assert data["sessions"][0]["ticker"] == "SBER"


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

    response = client.get("/api/sessions")

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

    response = client.get("/api/session/LKOH")

    assert response.status_code == 200

    data = response.json()

    assert data["ticker"] == "LKOH"
    assert data["status"] == "ACTIVE"
    assert data["current_price"] == 4453


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

    response = client.post("/api/stop-session/VTBR")

    assert response.status_code == 200

    data = response.json()

    assert data["ticker"] == "VTBR"
    assert data["status"] == "REMOVED"
    assert data["removed"] is True

    sessions_response = client.get("/api/sessions")
    sessions_data = sessions_response.json()

    tickers = {
        session["ticker"]
        for session in sessions_data["sessions"]
    }

    assert "VTBR" not in tickers

def test_api_usage_endpoint_returns_summary() -> None:
    client = TestClient(app)

    response = client.get("/api/api-usage")

    assert response.status_code == 200

    data = response.json()

    assert "total_weight" in data
    assert "events_count" in data
    assert "by_operation" in data

from dataclasses import dataclass, field
from decimal import Decimal

from application.sandbox_session_registry import (
    sandbox_session_registry,
)


@dataclass(slots=True)
class FakePosition:
    quantity: int


@dataclass(slots=True)
class FakeGridEngine:
    open_positions: dict[int, FakePosition] = field(
        default_factory=dict
    )
    realized_profit: Decimal = Decimal("0")


@dataclass(slots=True)
class FakeSandboxSession:
    current_price: Decimal
    grid_engine: FakeGridEngine
    unrealized_profit: Decimal = Decimal("0")


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
            current_price=Decimal("333"),
            grid_engine=FakeGridEngine(
                open_positions={
                    1: FakePosition(
                        quantity=10,
                    )
                },
                realized_profit=Decimal("12"),
            ),
            unrealized_profit=Decimal("5"),
        ),
    )

    response = client.get("/api/session/SBER")

    assert response.status_code == 200

    data = response.json()

    assert data["ticker"] == "SBER"
    assert data["current_price"] == 333.0
    assert data["positions"] == 1
    assert data["quantity"] == 10
    assert data["realized_profit"] == 12.0
    assert data["unrealized_profit"] == 5.0
    assert data["total_profit"] == 17.0

    sandbox_session_registry.unregister(
        ticker="SBER",
    )
