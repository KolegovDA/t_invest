from __future__ import annotations

import os
import sqlite3
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import head_server.app as head_app
from head_server.storage import HeadStorage


@pytest.fixture
def head_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    storage = HeadStorage(db_path=str(tmp_path / "head.db"))
    monkeypatch.setattr(head_app, "storage", storage)
    return TestClient(head_app.app)


def register_client(client: TestClient, login: str) -> dict:
    response = client.post(
        "/head/api/clients/register",
        json={
            "full_name": "Пётр Петров",
            "phone": "+79001112233",
            "email": "petr@example.com",
            "birth_date": "1985-05-05",
            "login": login,
            "password_hash": "salt$digest",
        },
    )
    assert response.status_code == 200
    return response.json()


def admin_login(client: TestClient) -> None:
    response = client.post(
        "/head/api/admin/login",
        json={
            "login": os.getenv("HEAD_ADMIN_LOGIN", "admin"),
            "password": os.getenv("HEAD_ADMIN_PASSWORD", "esm-admin"),
        },
    )
    assert response.status_code == 200


def send_heartbeat(
    client: TestClient,
    api_key: str,
    device_key: str,
    machine_label: str = "PC-TEST",
) -> None:
    response = client.post(
        "/head/api/clients/heartbeat",
        headers={"X-Api-Key": api_key},
        json={"device_key": device_key, "machine_label": machine_label},
    )
    assert response.status_code == 200


def test_overview_stats_and_daily(head_client: TestClient) -> None:
    client = head_client
    assert client.get("/head/api/admin/overview").status_code == 401

    registered = register_client(client, "overviewuser")
    api_key = registered["api_key"]
    send_heartbeat(client, api_key, "device-overview-1", "Рабочий ПК")
    send_heartbeat(client, api_key, "device-overview-1", "Рабочий ПК")
    send_heartbeat(client, api_key, "device-overview-2", "Ноутбук")
    admin_login(client)

    response = client.get("/head/api/admin/overview", params={"days": 30})
    assert response.status_code == 200
    data = response.json()
    assert data["stats"] == {
        "clients_total": 1,
        "clients_active_24h": 0,
        "devices_total": 2,
        "devices_online": 2,
        "topups_pending": 0,
    }
    assert len(data["daily"]) == 30
    assert [day["copies"] for day in data["daily"]] == [0] * 29 + [2]
    assert data["daily"][-1]["day"] == datetime.now(timezone.utc).date().isoformat()

    full = client.get("/head/api/admin/overview").json()
    assert len(full["daily"]) == 7
    assert full["daily"][-1]["copies"] == 2
    assert len(client.get("/head/api/admin/overview?days=1").json()["daily"]) == 1
    assert len(client.get("/head/api/admin/overview?days=500").json()["daily"]) == 180

    old_time = (datetime.now(timezone.utc) - timedelta(minutes=6)).isoformat()
    with sqlite3.connect(head_app.storage.db_path) as connection:
        connection.execute("UPDATE devices SET last_seen_at = ?", (old_time,))

    stale = client.get("/head/api/admin/overview").json()
    assert stale["stats"]["devices_online"] == 0
    assert stale["daily"][-1]["copies"] == 2


def test_overview_events_feed(head_client: TestClient) -> None:
    client = head_client
    registered = register_client(client, "eventsuser")
    api_key = registered["api_key"]
    send_heartbeat(client, api_key, "device-events-1", "Домашний ПК")
    send_heartbeat(client, api_key, "device-events-1", "Домашний ПК")

    topup = client.post(
        "/head/api/clients/topups",
        headers={"X-Api-Key": api_key},
        json={"amount": "250", "comment": "перевод с карты"},
    )
    assert topup.status_code == 201
    topup_id = topup.json()["request"]["id"]
    admin_login(client)
    assert client.post(
        f"/head/api/admin/topups/{topup_id}/approve",
        json={"review_note": "ок"},
    ).status_code == 200

    response = client.get("/head/api/admin/overview")
    assert response.status_code == 200
    data = response.json()
    assert data["stats"]["topups_pending"] == 0
    events = data["events"]
    assert {event["type"] for event in events} == {
        "client_registered",
        "device_first_seen",
        "topup_created",
        "topup_approved",
    }
    assert len(events) == 4
    assert all(event["client_login"] == "eventsuser" for event in events)
    assert [event["at"] for event in events] == sorted(
        (event["at"] for event in events), reverse=True
    )
    by_type = {event["type"]: event for event in events}
    assert by_type["client_registered"]["details"] == "eventsuser"
    assert by_type["device_first_seen"]["details"] == "Домашний ПК"
    assert by_type["topup_created"]["amount"] == "250.00"
    assert by_type["topup_approved"]["details"] == "ок"


def test_overview_empty(head_client: TestClient) -> None:
    admin_login(head_client)
    response = head_client.get("/head/api/admin/overview")
    assert response.status_code == 200
    data = response.json()
    assert data["stats"]["devices_online"] == 0
    assert data["events"] == []
    assert len(data["daily"]) == 7
    assert all(day["copies"] == 0 for day in data["daily"])


def test_admin_activity_online_users(head_client: TestClient) -> None:
    client = head_client
    first = register_client(client, "onlineuser")
    second = register_client(client, "offlineuser")
    send_heartbeat(client, first["api_key"], "online-pc", "Рабочий")
    send_heartbeat(client, first["api_key"], "online-laptop", "Ноутбук")
    send_heartbeat(client, second["api_key"], "offline-pc", "Старый ПК")

    assert client.get("/head/api/admin/activity").status_code == 401
    admin_login(client)
    old_time = (datetime.now(timezone.utc) - timedelta(minutes=6)).isoformat()
    with sqlite3.connect(head_app.storage.db_path) as connection:
        connection.execute(
            "UPDATE devices SET last_seen_at = ? WHERE device_key = ?",
            (old_time, "offline-pc"),
        )

    response = client.get("/head/api/admin/activity")
    assert response.status_code == 200
    data = response.json()
    assert data["online_seconds"] == 300
    assert len(data["users"]) == 1
    user = data["users"][0]
    assert user["client"]["login"] == "onlineuser"
    assert "api_key" not in user["client"]
    assert user["online_devices"] == 2
    assert {device["machine_label"] for device in user["devices"]} == {
        "Рабочий", "Ноутбук"
    }
    assert all(device["online"] for device in user["devices"])

    with sqlite3.connect(head_app.storage.db_path) as connection:
        connection.execute("UPDATE devices SET last_seen_at = ?", (old_time,))

    assert client.get("/head/api/admin/activity").json()["users"] == []


def test_admin_client_profile_and_cabinet_balance(head_client: TestClient) -> None:
    client = head_client
    registered = register_client(client, "profileuser")
    client_id = registered["client"]["id"]
    api_key = registered["api_key"]
    profile_url = f"/head/api/admin/clients/{client_id}/profile"

    assert client.get(profile_url).status_code == 401
    admin_login(client)
    assert client.get("/head/api/admin/clients/999999/profile").status_code == 404

    empty = client.get(profile_url).json()
    assert empty["client"]["login"] == "profileuser"
    assert empty["accounts"] == []
    assert empty["cabinet_balance"] == "0"
    assert "api_key" not in empty["client"]
    assert "password_hash" not in empty["client"]

    head_app.storage.store_sync(
        client_id=client_id,
        payload={
            "accounts": [
                {
                    "id": 1,
                    "name": "Рабочий счёт",
                    "broker": "t_invest",
                    "broker_account_id": "12345",
                    "mode": "live",
                    "enabled": True,
                    "historical_balance": "15000.00",
                    "api_key": "must-not-be-returned",
                },
                {"name": "Демо", "broker": "bybit", "mode": "demo"},
            ],
        },
    )
    head_app.storage.set_commission_percent(client_id, "t_invest", Decimal("17.5"))
    head_app.storage.record_commission_charge(
        client_id,
        {"broker": "t_invest", "amount": "25.00", "balance_after": "-25.00"},
    )

    listing = client.get("/head/api/admin/clients").json()["clients"]
    row = next(item for item in listing if item["id"] == client_id)
    assert Decimal(row["cabinet_balance"]) == Decimal("-25.00")
    assert "api_key" not in row
    assert "latest_payload" not in row

    data = client.get(profile_url).json()
    assert Decimal(data["cabinet_balance"]) == Decimal("-25.00")
    assert data["default_percent"] == 30
    assert data["commission_settings"] == {"t_invest": "17.5"}
    assert len(data["accounts"]) == 2
    assert data["accounts"][0]["name"] == "Рабочий счёт"
    assert data["accounts"][0]["historical_balance"] == "15000.00"
    assert "api_key" not in data["accounts"][0]
    assert data["accounts"][1]["broker"] == "bybit"
    assert data["accounts"][1]["historical_balance"] is None

    created = client.post(
        "/head/api/clients/topups",
        headers={"X-Api-Key": api_key},
        json={"amount": "100"},
    ).json()["request"]
    assert client.post(
        f"/head/api/admin/topups/{created['id']}/approve", json={}
    ).status_code == 200
    updated = client.get("/head/api/admin/clients").json()["clients"]
    row = next(item for item in updated if item["id"] == client_id)
    assert Decimal(row["cabinet_balance"]) == Decimal("75.00")


def test_overview_daily_metrics_series(head_client: TestClient) -> None:
    client = head_client
    registered = register_client(client, "metricuser")
    api_key = registered["api_key"]
    client_id = registered["client"]["id"]
    send_heartbeat(client, api_key, "device-metric-1", "ПК метрик")
    head_app.storage.store_sync(client_id=client_id, payload={"accounts": []})
    topup = client.post(
        "/head/api/clients/topups",
        headers={"X-Api-Key": api_key},
        json={"amount": "100"},
    )
    assert topup.status_code == 201
    admin_login(client)

    data = client.get("/head/api/admin/overview", params={"days": 7}).json()
    assert len(data["daily"]) == 7
    today = data["daily"][-1]
    assert today["copies"] == 1
    assert today["devices_online"] == 1
    assert today["clients_total"] == 1
    assert today["devices_total"] == 1
    assert today["clients_active_24h"] == 1
    assert today["topups_pending"] == 1
    assert data["daily"][0]["clients_total"] == 0
    assert data["daily"][0]["topups_pending"] == 0

    all_time = client.get(
        "/head/api/admin/overview", params={"all_time": "true"}
    ).json()
    assert len(all_time["daily"]) == 1
    assert all_time["daily"][-1]["clients_total"] == 1
    assert all_time["daily"][-1]["topups_pending"] == 1

    approved = client.post(
        f"/head/api/admin/topups/{topup.json()['request']['id']}/approve", json={}
    )
    assert approved.status_code == 200

    data = client.get("/head/api/admin/overview", params={"days": 7}).json()
    assert data["daily"][-1]["topups_pending"] == 0
    assert data["stats"]["topups_pending"] == 0


def test_sync_keeps_accounts_from_multiple_devices_and_source_address(head_client):
    import json

    registered = register_client(head_client, "multi-device")
    headers = {"X-Api-Key": registered["api_key"]}
    for device, broker_account, balance in [("one", "broker-one", "100"), ("two", "broker-two", "200")]:
        response = head_client.post("/head/api/sync", headers=headers, json={
            "device_key": device, "software_endpoint": f"http://{device}-pc:8001", "payload": {"accounts": [{
                "id": device, "broker": "tinvest", "broker_account_id": broker_account,
                "mode": "live", "historical_balance": balance, "instruments": ["SBER"],
            }], "platforms": ["tinvest"], "instruments": ["SBER"],
                "sessions": [{"session_id": f"session-{device}", "status": "RUNNING"}],
                "closed_grids": [{"grid_id": f"grid-{device}", "profit": "1"}],
                "balance_history": [{"trading_account_id": device, "created_at": "2026-10-03", "currency": "RUB", "equity": balance}],
            },
        })
        assert response.status_code == 200
    stored = head_app.storage.get_client_by_id(registered["client"]["id"])
    merged = json.loads(stored.latest_payload)
    assert len(merged["accounts"]) == 2
    assert merged["current_balance"] == "300"
    assert {row["grid_id"] for row in merged["closed_grids"]} == {"grid-one", "grid-two"}
    assert len(merged["sessions"]) == 2
    assert len(merged["balance_history"]) == 2
    assert head_client.post("/head/api/sync", headers=headers, json={"device_key": "two", "payload": merged}).status_code == 200
    retried = json.loads(head_app.storage.get_client_by_id(registered["client"]["id"]).latest_payload)
    assert len(retried["closed_grids"]) == 2
    assert len(retried["sessions"]) == 2
    assert len(retried["balance_history"]) == 2
    devices = head_app.storage.list_devices()
    assert all(device["source_address"] for device in devices)
    assert {device["software_endpoint"] for device in devices} == {"http://one-pc:8001", "http://two-pc:8001"}
    assert all(not device["reverse_reachability_verified"] for device in devices)
    assert {device["software_endpoint"] for device in HeadStorage(head_app.storage.db_path).list_devices()} == {"http://one-pc:8001", "http://two-pc:8001"}
    assert head_app.storage.get_asset_trading_settings()["tinvest"]["SBER"]["trailing_percent"] is None


def test_overview_all_time_from_earliest_event(head_client: TestClient) -> None:
    client = head_client
    register_client(client, "olduser")
    old_day = (datetime.now(timezone.utc) - timedelta(days=5)).date().isoformat()
    with sqlite3.connect(head_app.storage.db_path) as connection:
        connection.execute(
            "UPDATE clients SET created_at = ? WHERE login = 'olduser'",
            (old_day + "T12:00:00+00:00",),
        )

    admin_login(client)
    data = client.get(
        "/head/api/admin/overview", params={"all_time": "true"}
    ).json()
    assert len(data["daily"]) == 6
    assert data["daily"][0]["day"] == old_day
    assert data["daily"][0]["clients_total"] == 1
    assert data["daily"][3]["clients_total"] == 1
    assert data["daily"][-1]["clients_total"] == 1

    window = client.get("/head/api/admin/overview", params={"days": 1}).json()
    assert len(window["daily"]) == 1
    assert window["daily"][-1]["clients_total"] == 1
