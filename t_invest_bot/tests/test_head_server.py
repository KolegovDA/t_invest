from __future__ import annotations

import os

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


def test_browser_devices_are_separate_from_installations_and_idempotent(tmp_path):
    from datetime import datetime, timezone
    storage = HeadStorage(str(tmp_path / "browser.db"))
    now = datetime.now(timezone.utc).isoformat()
    devices = [{"device_id": "phone-a", "last_seen_at": now}, {"device_id": "phone-b", "last_seen_at": now}]
    storage.upsert_device(1, "installation")
    storage.store_browser_devices(1, "installation", devices)
    storage.store_browser_devices(1, "installation", devices)
    assert len(storage.list_devices()) == 1
    assert len(storage.list_browser_devices()) == 2
    old_time = "2026-01-01T00:00:00+00:00"
    storage.store_browser_devices(1, "installation", [{"device_id": "phone-a", "last_seen_at": old_time}])
    recorded = {item["device_id"]: item["last_seen_at"] for item in storage.list_browser_devices()}
    assert recorded["phone-a"] == now
    storage.store_browser_devices(1, "installation", [{"device_id": "phone-c", "last_seen_at": old_time}])
    assert storage.list_browser_devices()[-1]["last_seen_at"] == old_time


def setup_module() -> None:
    global ORIGINAL_DB_PATH

    ORIGINAL_DB_PATH = (
        os.getenv(
            "HEAD_DB_PATH"
        )
    )

    test_db = (
        "head_test_"
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
                    "Иван Иванов"
                ),

                "phone": (
                    "+79001234567"
                ),

                "email": (
                    "ivan@example.com"
                ),

                "birth_date": (
                    "1990-01-01"
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


def test_health() -> None:
    client = (
        TestClient(
            head_app.app
        )
    )

    response = (
        client.get(
            "/head/api/health"
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
            "status"
        ]
        == "ok"
    )


def test_register_login_sync_flow() -> None:
    client = (
        TestClient(
            head_app.app
        )
    )

    registered = (
        register_client(
            client,

            "ivan",
        )
    )

    api_key = (
        registered[
            "api_key"
        ]
    )

    assert (
        api_key
    )

    #
    # Повторная регистрация
    # того же логина
    # отклоняется.
    #
    duplicate = (
        client.post(
            "/head/api/clients/register",

            json={
                "full_name": "X",
                "phone": "1",
                "email": "x@x",
                "birth_date": "2000-01-01",
                "login": "ivan",
                "password_hash": "h",
            },
        )
    )

    assert (
        duplicate
        .status_code
        == 400
    )

    #
    # Логин с тем же хэшем
    # возвращает api_key.
    #
    login_response = (
        client.post(
            "/head/api/clients/login",

            json={
                "login": "ivan",

                "password_hash": (
                    "salt$digest"
                ),
            },
        )
    )

    assert (
        login_response
        .status_code
        == 200
    )

    assert (
        login_response
        .json()[
            "api_key"
        ]
        == (
            api_key
        )
    )

    #
    # Неверный пароль.
    #
    bad_login = (
        client.post(
            "/head/api/clients/login",

            json={
                "login": "ivan",

                "password_hash": (
                    "other"
                ),
            },
        )
    )

    assert (
        bad_login
        .status_code
        == 401
    )

    #
    # Sync требует api_key.
    #
    unauthorized = (
        client.post(
            "/head/api/sync",

            json={
                "payload": {}
            },
        )
    )

    assert (
        unauthorized
        .status_code
        == 401
    )

    sync_response = (
        client.post(
            "/head/api/sync",

            headers={
                "X-Api-Key": (
                    api_key
                ),
            },

            json={
                "payload": {
                    "accounts": [
                        {
                            "broker_account_id": (
                                "123"
                            ),
                        }
                    ],

                    "platforms": [
                        "tinvest"
                    ],

                    "instruments": [
                        "SBER"
                    ],

                    "initial_balance": (
                        "100000"
                    ),

                    "current_balance": (
                        "105000"
                    ),

                    "total_profit": (
                        "5000"
                    ),

                    "roe_percent": (
                        "5"
                    ),
                }
            },
        )
    )

    assert (
        sync_response
        .status_code
        == 200
    )

    #
    # Админ видит клиента
    # с метриками.
    #
    admin_login = (
        client.post(
            "/head/api/admin/login",

            json={
                "login": (
                    os.getenv(
                        "HEAD_ADMIN_LOGIN",

                        "admin",
                    )
                ),

                "password": (
                    os.getenv(
                        "HEAD_ADMIN_PASSWORD",

                        "esm-admin",
                    )
                ),
            },
        )
    )

    assert (
        admin_login
        .status_code
        == 200
    )

    clients_response = (
        client.get(
            "/head/api/admin/clients"
        )
    )

    assert (
        clients_response
        .status_code
        == 200
    )

    clients = (
        clients_response
        .json()[
            "clients"
        ]
    )

    assert (
        len(
            clients
        )
        >= 1
    )

    ivan = [
        item

        for item
        in clients

        if (
            item[
                "login"
            ]
            == "ivan"
        )
    ][0]

    assert (
        ivan[
            "platforms"
        ]
        == [
            "tinvest"
        ]
    )

    assert (
        ivan[
            "instruments"
        ]
        == [
            "SBER"
        ]
    )

    assert (
        ivan[
            "total_profit"
        ]
        == "5000"
    )

    assert (
        ivan[
            "roe_percent"
        ]
        == "5"
    )

    syncs_response = (
        client.get(
            "/head/api/admin/clients"
            f"/{ivan['id']}"
            "/syncs"
        )
    )

    assert (
        syncs_response
        .status_code
        == 200
    )

    syncs = (
        syncs_response
        .json()[
            "syncs"
        ]
    )

    assert (
        len(
            syncs
        )
        == 1
    )

    assert (
        syncs[0]
        ["payload"][
            "platforms"
        ]
        == [
            "tinvest"
        ]
    )


def test_admin_requires_auth() -> None:
    client = (
        TestClient(
            head_app.app
        )
    )

    response = (
        client.get(
            "/head/api/admin/clients"
        )
    )

    assert (
        response
        .status_code
        == 401
    )


def test_password_reset_flow() -> None:
    client = (
        TestClient(
            head_app.app
        )
    )

    register_client(
        client,
        "resetuser",
    )

    #
    # Без админской
    # куки выдача кода
    # запрещена.
    #
    unauth = (
        client.post(
            "/head/api/admin/clients"
            "/1/reset-password"
        )
    )

    assert (
        unauth
        .status_code
        == 401
    )

    admin_login = (
        client.post(
            "/head/api/admin/login",

            json={
                "login": (
                    os.getenv(
                        "HEAD_ADMIN_LOGIN",

                        "admin",
                    )
                ),

                "password": (
                    os.getenv(
                        "HEAD_ADMIN_PASSWORD",

                        "esm-admin",
                    )
                ),
            },
        )
    )

    assert (
        admin_login
        .status_code
        == 200
    )

    clients_response = (
        client.get(
            "/head/api/admin/clients"
        )
    )

    resetuser = [
        item

        for item
        in clients_response
        .json()[
            "clients"
        ]

        if (
            item[
                "login"
            ]
            == "resetuser"
        )
    ][0]

    missing = (
        client.post(
            "/head/api/admin/clients"
            "/999999/reset-password"
        )
    )

    assert (
        missing
        .status_code
        == 404
    )

    issue = (
        client.post(
            "/head/api/admin/clients"
            f"/{resetuser['id']}"
            "/reset-password"
        )
    )

    assert (
        issue
        .status_code
        == 200
    )

    issued = (
        issue
        .json()
    )

    assert (
        issued[
            "login"
        ]
        == "resetuser"
    )

    assert (
        len(
            issued[
                "reset_code"
            ]
        )
        == 6
    )

    wrong = (
        client.post(
            "/head/api/clients/"
            "password-reset/confirm",

            json={
                "login": (
                    "resetuser"
                ),

                "code": (
                    "000000"
                ),

                "new_password_hash": (
                    "salt$newdigest"
                ),
            },
        )
    )

    assert (
        wrong
        .status_code
        == 400
    )

    confirm = (
        client.post(
            "/head/api/clients/"
            "password-reset/confirm",

            json={
                "login": (
                    "resetuser"
                ),

                "code": (
                    issued[
                        "reset_code"
                    ]
                ),

                "new_password_hash": (
                    "salt$newdigest"
                ),
            },
        )
    )

    assert (
        confirm
        .status_code
        == 200
    )

    confirmed = (
        confirm
        .json()
    )

    assert (
        confirmed[
            "client"
        ][
            "login"
        ]
        == "resetuser"
    )

    assert (
        confirmed[
            "api_key"
        ]
    )

    #
    # Код одноразовый.
    #
    reuse = (
        client.post(
            "/head/api/clients/"
            "password-reset/confirm",

            json={
                "login": (
                    "resetuser"
                ),

                "code": (
                    issued[
                        "reset_code"
                    ]
                ),

                "new_password_hash": (
                    "salt$again"
                ),
            },
        )
    )

    assert (
        reuse
        .status_code
        == 400
    )

    #
    # Вход со старым
    # паролем больше
    # не работает.
    #
    old_login = (
        client.post(
            "/head/api/clients/login",

            json={
                "login": (
                    "resetuser"
                ),

                "password_hash": (
                    "salt$digest"
                ),
            },
        )
    )

    assert (
        old_login
        .status_code
        == 401
    )

    #
    # Вход с новым
    # паролем работает.
    #
    new_login = (
        client.post(
            "/head/api/clients/login",

            json={
                "login": (
                    "resetuser"
                ),

                "password_hash": (
                    "salt$newdigest"
                ),
            },
        )
    )

    assert (
        new_login
        .status_code
        == 200
    )


def test_devices_heartbeat_and_admin() -> None:
    client = (
        TestClient(
            head_app.app
        )
    )

    registered = (
        register_client(
            client,

            "deviceuser",
        )
    )

    api_key = (
        registered[
            "api_key"
        ]
    )
    from datetime import datetime, timezone
    browser_batch = {"installation_key": "dev-1", "devices": [
        {"device_id": "phone-a", "last_seen_at": datetime.now(timezone.utc).isoformat()},
        {"device_id": "phone-b", "last_seen_at": datetime.now(timezone.utc).isoformat()},
    ]}
    assert client.post("/head/api/clients/browser-devices", json=browser_batch).status_code == 401
    assert client.post("/head/api/clients/browser-devices", json=browser_batch, headers={"X-Api-Key": api_key}).status_code == 200

    unauthorized = (
        client.post(
            "/head/api/clients"
            "/heartbeat",

            json={
                "device_key": (
                    "dev-1"
                ),
            },
        )
    )

    assert (
        unauthorized
        .status_code
        == 401
    )

    empty_key = (
        client.post(
            "/head/api/clients"
            "/heartbeat",

            headers={
                "X-Api-Key": (
                    api_key
                ),
            },

            json={
                "device_key": (
                    "   "
                ),
            },
        )
    )

    assert (
        empty_key
        .status_code
        == 400
    )

    heartbeat = (
        client.post(
            "/head/api/clients"
            "/heartbeat",

            headers={
                "X-Api-Key": (
                    api_key
                ),
            },

            json={
                "device_key": (
                    "dev-1"
                ),

                "machine_label": (
                    "PC-TEST"
                ),
            },
        )
    )

    assert (
        heartbeat
        .status_code
        == 200
    )

    sync_with_device = (
        client.post(
            "/head/api/sync",

            headers={
                "X-Api-Key": (
                    api_key
                ),
            },

            json={
                "payload": {
                    "current_balance": (
                        "100"
                    ),
                },

                "device_key": (
                    "dev-2"
                ),

                "machine_label": (
                    "PC-2"
                ),
            },
        )
    )

    assert (
        sync_with_device
        .status_code
        == 200
    )

    admin_login = (
        client.post(
            "/head/api/admin/login",

            json={
                "login": (
                    os.getenv(
                        "HEAD_ADMIN_LOGIN",

                        "admin",
                    )
                ),

                "password": (
                    os.getenv(
                        "HEAD_ADMIN_PASSWORD",

                        "esm-admin",
                    )
                ),
            },
        )
    )

    assert (
        admin_login
        .status_code
        == 200
    )

    devices_response = (
        client.get(
            "/head/api/admin/devices"
        )
    )
    assert len(devices_response.json()["browser_devices"]) == 2

    assert (
        devices_response
        .status_code
        == 200
    )

    devices = (
        devices_response
        .json()[
            "devices"
        ]
    )

    by_key = {
        item[
            "device_key"
        ]: item

        for item
        in devices
    }

    assert (
        "dev-1"
        in by_key
    )

    assert (
        "dev-2"
        in by_key
    )

    assert (
        by_key[
            "dev-1"
        ][
            "online"
        ]
        is True
    )

    assert (
        by_key[
            "dev-1"
        ][
            "client_login"
        ]
        == (
            "deviceuser"
        )
    )

    assert (
        by_key[
            "dev-1"
        ][
            "is_head"
        ]
        is False
    )

    set_head = (
        client.post(
            "/head/api/admin/devices"

            f"/{by_key['dev-1']['id']}"
            "/head",

            json={
                "is_head": (
                    True
                ),
            },
        )
    )

    assert (
        set_head
        .status_code
        == 200
    )

    devices_after = (
        client.get(
            "/head/api/admin/devices"
        )
        .json()[
            "devices"
        ]
    )

    marked = [
        item

        for item
        in (
            devices_after
        )

        if (
            item[
                "device_key"
            ]
            == (
                "dev-1"
            )
        )
    ][0]

    assert (
        marked[
            "is_head"
        ]
        is True
    )

    missing_device = (
        client.post(
            "/head/api/admin/devices"
            "/999999/head",

            json={
                "is_head": (
                    True
                ),
            },
        )
    )

    assert (
        missing_device
        .status_code
        == 404
    )

    history = (
        client.get(
            "/head/api/clients"
            "/history",

            headers={
                "X-Api-Key": (
                    api_key
                ),
            },
        )
    )

    assert (
        history
        .status_code
        == 200
    )

    history_data = (
        history
        .json()
    )

    assert (
        history_data[
            "client"
        ][
            "login"
        ]
        == (
            "deviceuser"
        )
    )

    assert (
        len(
            history_data[
                "syncs"
            ]
        )
        >= 1
    )
