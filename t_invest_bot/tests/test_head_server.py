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
