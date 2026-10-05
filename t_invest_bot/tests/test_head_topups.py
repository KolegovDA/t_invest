from __future__ import annotations

import base64
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


DOCUMENT_BYTES = (
    b"PNG-DATA-123"
)


DOCUMENT_BASE64 = (
    base64
    .b64encode(
        DOCUMENT_BYTES
    )
    .decode(
        "ascii"
    )
)


def setup_module() -> None:
    global ORIGINAL_DB_PATH

    ORIGINAL_DB_PATH = (
        os.getenv(
            "HEAD_DB_PATH"
        )
    )

    test_db = (
        "head_topups_test_"
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
        client
        .post(
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


def admin_login(
    client: TestClient,
) -> None:
    response = (
        client
        .post(
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
        response
        .status_code
        == 200
    )


def create_topup(
    client: TestClient,

    api_key: str,

    amount: str,

    with_document: bool = (
        True
    ),
) -> dict:
    body = {
        "amount": (
            amount
        ),

        "comment": (
            "пополнение счёта"
        ),
    }

    if with_document:
        body[
            "document_name"
        ] = (
            "чек.png"
        )

        body[
            "document_mime"
        ] = (
            "image/png"
        )

        body[
            "document_base64"
        ] = (
            DOCUMENT_BASE64
        )

    response = (
        client
        .post(
            "/head/api/clients"
            "/topups",

            headers={
                "X-Api-Key": (
                    api_key
                ),
            },

            json=(
                body
            ),
        )
    )

    assert (
        response
        .status_code
        == 201
    )

    return (
        response
        .json()[
            "request"
        ]
    )


def test_topup_create_and_client_list() -> None:
    client = (
        TestClient(
            head_app.app
        )
    )

    registered = (
        register_client(
            client,

            "topupuser",
        )
    )

    api_key = (
        registered[
            "api_key"
        ]
    )

    unauthorized = (
        client
        .post(
            "/head/api/clients"
            "/topups",

            json={
                "amount": (
                    "100"
                ),
            },
        )
    )

    assert (
        unauthorized
        .status_code
        == 401
    )

    bad_amount = (
        client
        .post(
            "/head/api/clients"
            "/topups",

            headers={
                "X-Api-Key": (
                    api_key
                ),
            },

            json={
                "amount": (
                    "abc"
                ),
            },
        )
    )

    assert (
        bad_amount
        .status_code
        == 400
    )

    negative = (
        client
        .post(
            "/head/api/clients"
            "/topups",

            headers={
                "X-Api-Key": (
                    api_key
                ),
            },

            json={
                "amount": (
                    "-5"
                ),
            },
        )
    )

    assert (
        negative
        .status_code
        == 400
    )

    no_name = (
        client
        .post(
            "/head/api/clients"
            "/topups",

            headers={
                "X-Api-Key": (
                    api_key
                ),
            },

            json={
                "amount": (
                    "100"
                ),

                "document_base64": (
                    DOCUMENT_BASE64
                ),
            },
        )
    )

    assert (
        no_name
        .status_code
        == 400
    )

    broken_document = (
        client
        .post(
            "/head/api/clients"
            "/topups",

            headers={
                "X-Api-Key": (
                    api_key
                ),
            },

            json={
                "amount": (
                    "100"
                ),

                "document_name": (
                    "x.png"
                ),

                "document_base64": (
                    "!!!"
                ),
            },
        )
    )

    assert (
        broken_document
        .status_code
        == 400
    )

    created = (
        create_topup(
            client,

            api_key,

            "1500,50",
        )
    )

    assert (
        created[
            "status"
        ]
        == "pending"
    )

    assert (
        created[
            "amount"
        ]
        == "1500.50"
    )

    assert (
        created[
            "document_name"
        ]
        == "чек.png"
    )

    listing = (
        client
        .get(
            "/head/api/clients"
            "/topups",

            headers={
                "X-Api-Key": (
                    api_key
                ),
            },
        )
    )

    assert (
        listing
        .status_code
        == 200
    )

    data = (
        listing
        .json()
    )

    mine = [
        item

        for item
        in data[
            "requests"
        ]

        if (
            item[
                "id"
            ]
            == (
                created[
                    "id"
                ]
            )
        )
    ]

    assert (
        len(
            mine
        )
        == 1
    )

    assert (
        "document_data"
        not in (
            mine[0]
        )
    )

    assert (
        data[
            "balance"
        ]
        == "0"
    )


def test_topup_admin_review_flow() -> None:
    client = (
        TestClient(
            head_app.app
        )
    )

    registered = (
        register_client(
            client,

            "topupadmin",
        )
    )

    api_key = (
        registered[
            "api_key"
        ]
    )

    client_id = (
        registered[
            "client"
        ][
            "id"
        ]
    )

    first = (
        create_topup(
            client,

            api_key,

            "500",
        )
    )

    second = (
        create_topup(
            client,

            api_key,

            "700",

            with_document=(
                False
            ),
        )
    )

    unauth = (
        client
        .get(
            "/head/api/admin"
            "/topups"
        )
    )

    assert (
        unauth
        .status_code
        == 401
    )

    admin_login(
        client
    )

    listing = (
        client
        .get(
            "/head/api/admin"
            "/topups",

            params={
                "client_id": (
                    client_id
                ),
            },
        )
    )

    assert (
        listing
        .status_code
        == 200
    )

    data = (
        listing
        .json()
    )

    assert (
        len(
            data[
                "requests"
            ]
        )
        == 2
    )

    assert (
        data[
            "pending_count"
        ]
        >= 2
    )

    first_row = [
        item

        for item
        in data[
            "requests"
        ]

        if (
            item[
                "id"
            ]
            == (
                first[
                    "id"
                ]
            )
        )
    ][0]

    assert (
        first_row[
            "client_login"
        ]
        == "topupadmin"
    )

    missing = (
        client
        .post(
            "/head/api/admin"
            "/topups"
            "/999999/approve",

            json={
                "review_note": (
                    ""
                ),
            },
        )
    )

    assert (
        missing
        .status_code
        == 404
    )

    approve = (
        client
        .post(
            "/head/api/admin"
            f"/topups"
            f"/{first['id']}"
            "/approve",

            json={
                "review_note": (
                    "чек принят"
                ),
            },
        )
    )

    assert (
        approve
        .status_code
        == 200
    )

    approved = (
        approve
        .json()
    )

    assert (
        approved[
            "request"
        ][
            "status"
        ]
        == "approved"
    )

    assert (
        approved[
            "request"
        ][
            "balance_after"
        ]
        == "500.00"
    )

    assert (
        Decimal(
            approved[
                "balance"
            ]
        )
        == Decimal(
            "500.00"
        )
    )

    duplicate = (
        client
        .post(
            "/head/api/admin"
            f"/topups"
            f"/{first['id']}"
            "/approve",

            json={},
        )
    )

    assert (
        duplicate
        .status_code
        == 409
    )

    reject = (
        client
        .post(
            "/head/api/admin"
            f"/topups"
            f"/{second['id']}"
            "/reject",

            json={
                "review_note": (
                    "чек нечитаем"
                ),
            },
        )
    )

    assert (
        reject
        .status_code
        == 200
    )

    assert (
        reject
        .json()[
            "request"
        ][
            "status"
        ]
        == "rejected"
    )

    pending_after = (
        client
        .get(
            "/head/api/admin"
            "/topups",

            params={
                "client_id": (
                    client_id
                ),

                "status": (
                    "pending"
                ),
            },
        )
    )

    assert (
        pending_after
        .json()[
            "requests"
        ]
        == []
    )

    charges = (
        client
        .get(
            "/head/api/admin"
            "/commission"
            "/charges",

            params={
                "client_id": (
                    client_id
                ),
            },
        )
    )

    charge_row = (
        charges
        .json()[
            "charges"
        ][0]
    )

    assert (
        charge_row[
            "broker"
        ]
        == "topup"
    )

    assert (
        charge_row[
            "amount"
        ]
        == "-500.00"
    )

    assert (
        charge_row[
            "balance_after"
        ]
        == "500.00"
    )

    assert (
        Decimal(
            charges
            .json()[
                "balance"
            ]
        )
        == Decimal(
            "500.00"
        )
    )

    client_view = (
        client
        .get(
            "/head/api/clients"
            "/topups",

            headers={
                "X-Api-Key": (
                    api_key
                ),
            },
        )
    )

    client_data = (
        client_view
        .json()
    )

    by_id = {
        item[
            "id"
        ]: item

        for item
        in client_data[
            "requests"
        ]
    }

    assert (
        by_id[
            first[
                "id"
            ]
        ][
            "status"
        ]
        == "approved"
    )

    assert (
        by_id[
            second[
                "id"
            ]
        ][
            "review_note"
        ]
        == "чек нечитаем"
    )

    assert (
        Decimal(
            client_data[
                "balance"
            ]
        )
        == Decimal(
            "500.00"
        )
    )


def test_topup_document_access() -> None:
    client = (
        TestClient(
            head_app.app
        )
    )

    registered = (
        register_client(
            client,

            "topupdoc",
        )
    )

    api_key = (
        registered[
            "api_key"
        ]
    )

    with_doc = (
        create_topup(
            client,

            api_key,

            "300",
        )
    )

    without_doc = (
        create_topup(
            client,

            api_key,

            "400",

            with_document=(
                False
            ),
        )
    )

    unauth = (
        client
        .get(
            "/head/api/admin"
            f"/topups"
            f"/{with_doc['id']}"
            "/document"
        )
    )

    assert (
        unauth
        .status_code
        == 401
    )

    admin_login(
        client
    )

    document = (
        client
        .get(
            "/head/api/admin"
            f"/topups"
            f"/{with_doc['id']}"
            "/document"
        )
    )

    assert (
        document
        .status_code
        == 200
    )

    assert (
        document
        .content
        == (
            DOCUMENT_BYTES
        )
    )

    assert (
        document
        .headers[
            "content-type"
        ]
        .startswith(
            "image/png"
        )
    )

    assert (
        "filename"
        in (
            document
            .headers[
                "content-disposition"
            ]
        )
    )

    empty = (
        client
        .get(
            "/head/api/admin"
            f"/topups"
            f"/{without_doc['id']}"
            "/document"
        )
    )

    assert (
        empty
        .status_code
        == 404
    )

    missing = (
        client
        .get(
            "/head/api/admin"
            "/topups"
            "/999999/document"
        )
    )

    assert (
        missing
        .status_code
        == 404
    )
