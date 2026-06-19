from fastapi.testclient import TestClient

from web.api import app


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
