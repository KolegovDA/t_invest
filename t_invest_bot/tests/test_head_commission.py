from __future__ import annotations

import os

from decimal import (
    Decimal,
)
from fastapi.testclient import (
    TestClient,
)

import head_server.app as head_app

from head_server.storage import (
    HeadStorage,
)


ORIGINAL_DB_PATH = (
    None
)


def setup_module() -> None:
    global ORIGINAL_DB_PATH

    ORIGINAL_DB_PATH = (
        os.getenv(
            "HEAD_DB_PATH"
        )
    )

    test_db = (
        "head_commission_test_"
        + str(
            os.getpid()
        )
        + ".db"
    )

    os.environ[
        "HEAD_DB_PATH"
    ] = (
        test_db
    )

    head_app.storage = (
        HeadStorage(
            db_path=(
                test_db
            ),
        )
    )


def teardown_module() -> None:
    if (
        ORIGINAL_DB_PATH
        is None
    ):
        os.environ.pop(
            "HEAD_DB_PATH",
            None,
        )

    else:
        os.environ[
            "HEAD_DB_PATH"
        ] = (
            ORIGINAL_DB_PATH
        )


def register_client(
    client: TestClient,

    login: str,
) -> dict:
    response = (
        client.post(
            "/head/api/clients/register",

            json={
                "full_name": (
                    "Пётр Комиссионный"
                ),

                "phone": (
                    "+79005553535"
                ),

                "email": (
                    "commission@example.com"
                ),

                "birth_date": (
                    "1985-05-05"
                ),

                "login": (
                    login
                ),

                "password_hash": (
                    "salt$digest"
                ),
            },
        )
    )

    assert (
        response
        .status_code
        == 200
    )

    return (
        response
        .json()
    )


def admin_login(
    client: TestClient,
) -> None:
    response = (
        client.post(
            "/head/api/admin/login",

            json={
                "login": (
                    "admin"
                ),

                "password": (
                    "esm-admin"
                ),
            },
        )
    )

    assert (
        response
        .status_code
        == 200
    )


def test_config_returns_default_commission_without_settings() -> None:
    client = (
        TestClient(
            head_app.app
        )
    )

    registered = (
        register_client(
            client,

            "commission-default",
        )
    )

    api_key = (
        registered[
            "api_key"
        ]
    )

    response = (
        client.get(
            "/head/api/config",

            headers={
                "X-Api-Key": (
                    api_key
                ),
            },
        )
    )

    assert (
        response
        .status_code
        == 200
    )

    body = (
        response
        .json()
    )

    assert (
        body[
            "commission"
        ][
            "default_percent"
        ]
        == 30
    )

    assert (
        body[
            "commission"
        ][
            "by_platform"
        ]
        == {}
    )


def test_admin_sets_commission_and_config_returns_it() -> None:
    client = (
        TestClient(
            head_app.app
        )
    )

    admin_login(
        client
    )

    registered = (
        register_client(
            client,

            "commission-set",
        )
    )

    client_id = (
        registered[
            "client"
        ][
            "id"
        ]
    )

    response = (
        client.post(
            "/head/api/admin/commission",

            json={
                "client_id": (
                    client_id
                ),

                "platform": (
                    "TInvest"
                ),

                "percent": (
                    "15"
                ),
            },
        )
    )

    assert (
        response
        .status_code
        == 200
    )

    api_key = (
        registered[
            "api_key"
        ]
    )

    config = (
        client.get(
            "/head/api/config",

            headers={
                "X-Api-Key": (
                    api_key
                ),
            },
        )
        .json()
    )

    assert (
        config[
            "commission"
        ][
            "by_platform"
        ]
        == {
            "tinvest": (
                "15"
            )
        }
    )


def test_admin_commission_validates_percent() -> None:
    client = (
        TestClient(
            head_app.app
        )
    )

    admin_login(
        client
    )

    response = (
        client.post(
            "/head/api/admin/commission",

            json={
                "client_id": (
                    999999
                ),

                "platform": (
                    "tinvest"
                ),

                "percent": (
                    "150"
                ),
            },
        )
    )

    assert (
        response
        .status_code
        == 400
    )


def test_sync_stores_commission_charges_and_admin_reads_balance() -> None:
    client = (
        TestClient(
            head_app.app
        )
    )

    registered = (
        register_client(
            client,

            "commission-charges",
        )
    )

    client_id = (
        registered[
            "client"
        ][
            "id"
        ]
    )

    api_key = (
        registered[
            "api_key"
        ]
    )

    response = (
        client.post(
            "/head/api/sync",

            headers={
                "X-Api-Key": (
                    api_key
                ),
            },

            json={
                "payload": {
                    "accounts": [],

                    "commission_charges": [
                        {
                            "created_at": (
                                "2026-09-27T00:00:00+00:00"
                            ),

                            "broker": (
                                "tinvest"
                            ),

                            "instrument_id": (
                                "SBER_UID"
                            ),

                            "ticker": (
                                "SBER"
                            ),

                            "level_index": (
                                1
                            ),

                            "trade_profit": (
                                "100"
                            ),

                            "percent": (
                                "30"
                            ),

                            "amount": (
                                "30"
                            ),

                            "balance_after": (
                                "-30"
                            ),
                        },
                    ],
                },
            },
        )
    )

    assert (
        response
        .status_code
        == 200
    )

    admin_login(
        client
    )

    charges_response = (
        client.get(
            "/head/api/admin/commission/charges",

            params={
                "client_id": (
                    client_id
                ),
            },
        )
    )

    assert (
        charges_response
        .status_code
        == 200
    )

    body = (
        charges_response
        .json()
    )

    assert (
        len(
            body[
                "charges"
            ]
        )
        == 1
    )

    charge = (
        body[
            "charges"
        ][
            0
        ]
    )

    assert (
        charge[
            "ticker"
        ]
        == "SBER"
    )

    assert (
        charge[
            "amount"
        ]
        == "30"
    )

    assert (
        Decimal(
            body[
                "balance"
            ]
        )
        == Decimal(
            "-30"
        )
    )


def test_commission_retry_is_idempotent_per_device(tmp_path) -> None:
    storage = HeadStorage(str(tmp_path / "commissions.db"))
    charge = {
        "id": 1, "created_at": "2026-10-03T00:00:00+00:00",
        "broker": "tinvest", "trade_profit": "100", "percent": "30",
        "amount": "30", "balance_after": "-30", "trading_account_id": "account-1",
    }
    storage.record_commission_charge(1, charge, "device-one")
    storage.record_commission_charge(1, charge, "device-one")
    storage.record_commission_charge(1, charge, "device-two")
    assert len(storage.list_commission_charges(1)) == 2
    assert storage.get_commission_balance(1) == Decimal("-60")
    assert storage.list_commission_charges(1)[0]["trading_account_id"] == "account-1"


def test_sync_error_does_not_acknowledge_partial_commission_batch(tmp_path, monkeypatch) -> None:
    storage = HeadStorage(str(tmp_path / "retry.db"))
    monkeypatch.setattr(head_app, "storage", storage)
    client = TestClient(head_app.app)
    registered = register_client(client, "commission-retry")
    charge = {
        "id": 1, "created_at": "2026-10-03T00:00:00+00:00",
        "broker": "tinvest", "trade_profit": "100", "percent": "30",
        "amount": "30", "balance_after": "-30",
    }
    payload = {"device_key": "device", "payload": {"commission_charges": [charge, {**charge, "id": 2, "amount": "NaN"}]}}
    headers = {"X-Api-Key": registered["api_key"]}
    assert client.post("/head/api/sync", json=payload, headers=headers).status_code == 503
    payload["payload"]["commission_charges"][1]["amount"] = "30"
    assert client.post("/head/api/sync", json=payload, headers=headers).status_code == 200
    assert len(storage.list_commission_charges(registered["client"]["id"])) == 2


def test_trial_end_is_permanent_and_superpermission_is_admin_only(tmp_path, monkeypatch):
    storage = HeadStorage(str(tmp_path / "trial.db"))
    monkeypatch.setattr(head_app, "storage", storage)
    client = TestClient(head_app.app)
    registered = register_client(client, "trial-user")
    client_id = registered["client"]["id"]
    headers = {"X-Api-Key": registered["api_key"]}
    config = client.get("/head/api/config", headers=headers).json()
    assert config["entitlements"]["trial_active"]
    assert config["entitlements"]["can_start"]
    url = f"/head/api/admin/clients/{client_id}/balance"
    permissions = f"/head/api/admin/clients/{client_id}/permissions"
    assert client.post(url, json={"balance": "-500"}).status_code == 401
    assert client.post(permissions, json={"allow_insufficient_balance": True}, headers=headers).status_code == 401
    admin_login(client)
    assert client.post(url, json={"balance": "NaN"}).status_code == 400
    assert client.post(url, json={"balance": "-499"}).json()["entitlements"]["can_start"]
    ended = client.post(url, json={"balance": "-500"}).json()["entitlements"]
    assert not ended["trial_active"] and not ended["can_start"]
    assert not client.post(url, json={"balance": "0"}).json()["entitlements"]["can_start"]
    paid = client.post(url, json={"balance": "1"}).json()["entitlements"]
    assert paid["can_start"] and not paid["trial_active"]
    client.post(url, json={"balance": "-900"})
    assert client.post(permissions, json={"allow_insufficient_balance": True}).json()["entitlements"]["can_start"]
    assert not client.post(permissions, json={"allow_insufficient_balance": False}).json()["entitlements"]["can_start"]
    assert HeadStorage(storage.db_path).get_entitlements(client_id)["trial_ended_at"]
    from application.commission_service import CommissionService
    from infrastructure.sqlite.commission_repository import SQLiteCommissionRepository
    from infrastructure.sqlite.sqlite_database import SQLiteDatabase

    devices = []
    for name in ("one", "two"):
        database = SQLiteDatabase(tmp_path / f"{name}.db")
        database.initialize()
        devices.append(CommissionService(SQLiteCommissionRepository(database)))
    for device in devices:
        device.apply_head_config(client.get("/head/api/config", headers=headers).json())
        assert device.is_forced_drain()
    client.post(permissions, json={"allow_insufficient_balance": True})
    granted = client.get("/head/api/config", headers=headers).json()
    for device in devices:
        device.apply_head_config(granted)
        assert not device.is_forced_drain()
    client.post(permissions, json={"allow_insufficient_balance": False})
    revoked = client.get("/head/api/config", headers=headers).json()
    for device in devices:
        device.apply_head_config(revoked)
        assert device.is_forced_drain()
        assert CommissionService(device.repository).is_forced_drain()
    client.post(url, json={"balance": "1"})
    topped_up = client.get("/head/api/config", headers=headers).json()
    for device in devices:
        device.apply_head_config(topped_up)
        assert not device.is_forced_drain()
        assert not device.repository.load_entitlements()["trial_active"]


def test_admin_commission_requires_auth() -> None:
    client = (
        TestClient(
            head_app.app
        )
    )

    response = (
        client.get(
            "/head/api/admin/commission",
        )
    )

    assert (
        response
        .status_code
        == 401
    )
