from __future__ import annotations

import os

from pathlib import Path

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
        "head_control_logs_test_"
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
                    "Пётр Контрольный"
                ),

                "phone": (
                    "+79005553535"
                ),

                "email": (
                    "control@example.com"
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


def control_entry(
    source_id: int,
) -> dict:
    return {
        "source_id": (
            source_id
        ),

        "created_at": (
            "2026-09-30T00:00:00+00:00"
        ),

        "trading_account_id": (
            "2011718042"
        ),

        "instrument_id": (
            "ALRS_UID"
        ),

        "ticker": (
            "ALRS"
        ),

        "event_type": (
            "POSITION_CLEARED"
        ),

        "details": (
            "позиции закрыты вне бота, уровни освобождены"
        ),
    }


def push_control_logs(
    client: TestClient,
    api_key: str,
    entries: (
        list[dict]
    ),
) -> None:
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

                    "control_logs": (
                        entries
                    ),
                },
            },
        )
    )

    assert (
        response
        .status_code
        == 200
    )


def test_sync_stores_control_logs_and_admin_reads_them() -> None:
    client = (
        TestClient(
            head_app.app
        )
    )

    registered = (
        register_client(
            client,
            "control-logs-1",
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

    (
        push_control_logs(
            client,

            api_key,

            [
                control_entry(
                    1
                ),

                control_entry(
                    2
                ),
            ],
        )
    )

    admin_login(
        client
    )

    response = (
        client.get(
            "/head/api/admin/control-logs",
            params={
                "client_id": (
                    client_id
                ),
            },
        )
    )

    assert (
        response
        .status_code
        == 200
    )

    logs = (
        response
        .json()
        [
            "control_logs"
        ]
    )

    assert (
        len(
            logs
        )
        == 2
    )

    assert (
        logs[
            0
        ][
            "event_type"
        ]
        == (
            "POSITION_CLEARED"
        )
    )

    assert (
        logs[
            0
        ][
            "source_id"
        ]
        == 2
    )


def test_control_logs_deduplicated_by_source_id() -> None:
    client = (
        TestClient(
            head_app.app
        )
    )

    registered = (
        register_client(
            client,
            "control-logs-2",
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

    entry = (
        control_entry(
            7
        )
    )

    (
        push_control_logs(
            client,

            api_key,

            [
                entry
            ],
        )
    )

    (
        push_control_logs(
            client,

            api_key,

            [
                entry
            ],
        )
    )

    admin_login(
        client
    )

    response = (
        client.get(
            "/head/api/admin/control-logs",
            params={
                "client_id": (
                    client_id
                ),
            },
        )
    )

    assert (
        response
        .status_code
        == 200
    )

    assert (
        len(
            response
            .json()
            [
                "control_logs"
            ]
        )
        == 1
    )


def test_control_logs_admin_requires_auth() -> None:
    client = (
        TestClient(
            head_app.app
        )
    )

    response = (
        client.get(
            "/head/api/admin/control-logs",
        )
    )

    assert (
        response
        .status_code
        == 401
    )
