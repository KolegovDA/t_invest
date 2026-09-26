from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from pathlib import Path

from fastapi import (
    FastAPI,
    HTTPException,
    Request,
    Response,
)
from fastapi.middleware.cors import (
    CORSMiddleware,
)
from fastapi.responses import (
    FileResponse,
)
from pydantic import (
    BaseModel,
)

from head_server.storage import (
    HeadStorage,
    default_db_path,
)
from head_server.version import (
    HEAD_VERSION,
)


ADMIN_COOKIE = (
    "esm_head_admin"
)


def _admin_login() -> str:
    return (
        os.getenv(
            "HEAD_ADMIN_LOGIN",
            "admin",
        )
        .strip()
    )


def _admin_password() -> str:
    return (
        os.getenv(
            "HEAD_ADMIN_PASSWORD",
            "esm-admin",
        )
        .strip()
    )


storage = HeadStorage(
    db_path=(
        default_db_path()
    ),
)


app = FastAPI(
    title=(
        "ESM Head Server"
    ),

    version=(
        HEAD_VERSION
    ),
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# MODELS
# ============================================================

class ClientRegisterRequest(
    BaseModel
):
    full_name: str
    phone: str
    email: str
    birth_date: str
    login: str
    password_hash: str
    machine_label: str = ""


class ClientLoginRequest(
    BaseModel
):
    login: str
    password_hash: str


class SyncRequest(
    BaseModel
):
    payload: dict


class AdminLoginRequest(
    BaseModel
):
    login: str
    password: str


# ============================================================
# HELPERS
# ============================================================

def _client_dict(
    client,
    include_key: bool = (
        False
    ),
) -> dict:
    result = {
        "id": (
            client.id
        ),

        "created_at": (
            client
            .created_at
        ),

        "full_name": (
            client
            .full_name
        ),

        "phone": (
            client
            .phone
        ),

        "email": (
            client
            .email
        ),

        "birth_date": (
            client
            .birth_date
        ),

        "login": (
            client
            .login
        ),

        "machine_label": (
            client
            .machine_label
        ),

        "last_sync_at": (
            client
            .last_sync_at
        ),
    }

    if (
        include_key
    ):
        result[
            "api_key"
        ] = (
            client
            .api_key
        )

    return result


def _require_client(
    request: Request,
):
    api_key = (
        request
        .headers
        .get(
            "X-Api-Key",
        )

        or ""
    )

    if (
        not api_key
    ):
        authorization = (
            request
            .headers
            .get(
                "Authorization",
                "",
            )
        )

        if (
            authorization
            .startswith(
                "Bearer "
            )
        ):
            api_key = (
                authorization[
                    7:
                ]
            )

    client = (
        storage
        .get_client_by_api_key(
            api_key
        )
    )

    if (
        client
        is None
    ):
        raise HTTPException(
            status_code=401,
            detail=(
                "Invalid client api key"
            ),
        )

    return client


def _require_admin(
    request: Request,
) -> None:
    token = (
        request
        .cookies
        .get(
            ADMIN_COOKIE
        )
    )

    if (
        token
        != _admin_token()
    ):
        raise HTTPException(
            status_code=401,
            detail=(
                "Admin authorization "
                "required"
            ),
        )


def _admin_token() -> str:
    #
    # Токен админ-сессии —
    # производный от пароля:
    # смена пароля меняет
    # токен.
    #
    digest = (
        hashlib
        .sha256(
            (
                "esm-head:"
                + _admin_login()
                + ":"
                + _admin_password()
            )
            .encode(
                "utf-8"
            )
        )
        .hexdigest()
    )

    return digest


def _verify_client_password(
    password_hash: str,
    client,
) -> bool:
    return (
        hmac
        .compare_digest(
            password_hash,

            client
            .password_hash,
        )
    )


# ============================================================
# CLIENT API (для клиентских копий ПО)
# ============================================================

@app.get(
    "/head/api/health"
)
def health():
    return {
        "status": "ok",

        "version": (
            HEAD_VERSION
        ),
    }


@app.post(
    "/head/api/clients/register"
)
def client_register(
    request: (
        ClientRegisterRequest
    ),
):
    try:
        client = (
            storage
            .register_client(
                full_name=(
                    request
                    .full_name
                    .strip()
                ),

                phone=(
                    request
                    .phone
                    .strip()
                ),

                email=(
                    request
                    .email
                    .strip()
                ),

                birth_date=(
                    request
                    .birth_date
                    .strip()
                ),

                login=(
                    request
                    .login
                    .strip()
                ),

                password_hash=(
                    request
                    .password_hash
                ),

                machine_label=(
                    request
                    .machine_label
                ),
            )
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(
                error
            ),
        ) from error

    return {
        "client": (
            _client_dict(
                client
            )
        ),

        "api_key": (
            client
            .api_key
        ),
    }


@app.post(
    "/head/api/clients/login"
)
def client_login(
    request: (
        ClientLoginRequest
    ),
):
    client = (
        storage
        .get_client_by_login(
            request
            .login
            .strip()
        )
    )

    if (
        client
        is None
        or not (
            _verify_client_password(
                request
                .password_hash,

                client,
            )
        )
    ):
        raise HTTPException(
            status_code=401,
            detail=(
                "Invalid login "
                "or password"
            ),
        )

    return {
        "client": (
            _client_dict(
                client
            )
        ),

        "api_key": (
            client
            .api_key
        ),
    }


@app.post(
    "/head/api/sync"
)
def client_sync(
    request: (
        SyncRequest
    ),

    raw_request: Request,
):
    client = (
        _require_client(
            raw_request
        )
    )

    storage.store_sync(
        client_id=(
            client.id
        ),

        payload=(
            request
            .payload
        ),
    )

    return {
        "status": "ok",

        "server_time": (
            _now_iso()
        ),
    }


def _now_iso() -> str:
    from datetime import (
        datetime,
        timezone,
    )

    return (
        datetime
        .now(
            timezone.utc
        )
        .isoformat()
    )


@app.get(
    "/head/api/config"
)
def client_config(
    request: Request,
):
    _require_client(
        request
    )

    #
    # v1.3: здесь головной
    # сервер будет отдавать
    # комиссию по
    # пользователь/платформа.
    #
    return {
        "commission_default_percent": (
            30
        ),

        "version": (
            HEAD_VERSION
        ),
    }


# ============================================================
# ADMIN API + WEB UI
# ============================================================

@app.post(
    "/head/api/admin/login"
)
def admin_login(
    request: (
        AdminLoginRequest
    ),

    response: Response,
):
    if (
        request.login
        != _admin_login()

        or not (
            hmac
            .compare_digest(
                request
                .password,

                _admin_password(),
            )
        )
    ):
        raise HTTPException(
            status_code=401,
            detail=(
                "Неверный логин "
                "или пароль"
            ),
        )

    response.set_cookie(
        key=(
            ADMIN_COOKIE
        ),

        value=(
            _admin_token()
        ),

        max_age=(
            8
            * 60
            * 60
        ),

        samesite=(
            "lax"
        ),
    )

    return {
        "status": "ok",
    }


@app.get(
    "/head/api/admin/clients"
)
def admin_clients(
    request: Request,
):
    _require_admin(
        request
    )

    clients = (
        storage
        .list_clients()
    )

    return {
        "clients": [
            {
                **(
                    _client_dict(
                        client
                    )
                ),

                **(
                    storage
                    .client_metrics(
                        client
                    )
                ),
            }

            for client
            in clients
        ],
    }


@app.get(
    "/head/api/admin/clients"
    "/{client_id}/syncs"
)
def admin_client_syncs(
    client_id: int,

    request: Request,
):
    _require_admin(
        request
    )

    client = (
        storage
        .get_client_by_id(
            client_id
        )
    )

    if (
        client
        is None
    ):
        raise HTTPException(
            status_code=404,
            detail=(
                "Client not found"
            ),
        )

    return {
        "client": (
            _client_dict(
                client
            )
        ),

        "syncs": (
            storage
            .list_syncs(
                client_id=(
                    client_id
                ),
            )
        ),
    }


_STATIC_DIR = (
    Path(
        __file__
    )
    .parent
    / "static"
)


@app.get(
    "/"
)
def index():
    return FileResponse(
        _STATIC_DIR
        / "index.html"
    )
