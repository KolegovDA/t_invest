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
    assert response.json()["stage"] == "mvp"


def test_accounts_endpoint_returns_empty_accounts() -> None:
    client = TestClient(app)

    response = client.get("/api/accounts")

    assert response.status_code == 200
    assert response.json() == {
        "accounts": [],
    }
