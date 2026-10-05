from __future__ import annotations

import base64
import hashlib
import hmac
import os
from decimal import (
    Decimal,
)
from pathlib import Path
from urllib.parse import (
    quote,
)

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


RESET_CODE_TTL_SECONDS = (
    30 * 60
)


DEVICE_ONLINE_SECONDS = (
    5 * 60
)


TOPUP_MAX_DOCUMENT_BYTES = (
    8 * 1024 * 1024
)


TOPUP_MAX_AMOUNT = (
    Decimal(
        "100000000"
    )
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

    device_key: (
        str | None
    ) = None

    machine_label: str = ""
    software_endpoint: str | None = None


class HeartbeatRequest(
    BaseModel
):
    device_key: str

    machine_label: str = ""
    software_endpoint: str | None = None


class BrowserDevicesRequest(BaseModel):
    installation_key: str
    devices: list[dict]


class AdminLoginRequest(
    BaseModel
):
    login: str
    password: str


class AdminCommissionSetRequest(
    BaseModel
):
    client_id: int
    platform: str
    percent: str


class AdminTradingSettingsRequest(BaseModel):
    platform: str
    min_profit_percent: str
    entry_rebound_percent: str
    trailing_percent: str


class AdminBalanceRequest(BaseModel):
    balance: str
    note: str = ""


class AdminPermissionsRequest(BaseModel):
    allow_insufficient_balance: bool


class AdminAssetTradingSettingsRequest(BaseModel):
    platform: str
    ticker: str
    take_profit_percent: str | None = None
    max_take_profit_percent: str | None = None
    order_amount_multiplier: str | None = None
    max_order_amount_multiplier: str | None = None
    min_profit_percent: str | None = None
    entry_rebound_percent: str | None = None
    trailing_percent: str | None = None


class AdminDeviceHeadRequest(
    BaseModel
):
    is_head: bool


class ClientPasswordResetConfirmRequest(
    BaseModel
):
    login: str
    code: str
    new_password_hash: str


class ClientTopupRequest(
    BaseModel
):
    amount: str

    comment: str = ""

    document_name: (
        str | None
    ) = None

    document_mime: (
        str | None
    ) = None

    document_base64: (
        str | None
    ) = None


class AdminTopupReviewRequest(
    BaseModel
):
    review_note: str = ""


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
    "/head/api/clients/"
    "password-reset/confirm"
)
def client_password_reset_confirm(
    request: (
        ClientPasswordResetConfirmRequest
    ),
):
    try:
        client = (
            storage
            .confirm_password_reset(
                login=(
                    request
                    .login
                ),

                code=(
                    request
                    .code
                ),

                new_password_hash=(
                    request
                    .new_password_hash
                ),
            )
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,

            detail=(
                str(
                    error
                )
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

    if (
        request
        .device_key
    ):
        try:
            storage\
                .upsert_device(
                    client_id=(
                        client
                        .id
                    ),

                    device_key=(
                        request
                        .device_key
                    ),

                    machine_label=(
                        request
                        .machine_label
                    ),
                    source_address=raw_request.client.host if raw_request.client else None,
                    software_endpoint=request.software_endpoint,
                )

        except Exception as error:
            print(
                "DEVICE UPSERT ERROR:",
                repr(
                    error
                ),
            )

    storage.store_sync(
        client_id=(
            client.id
        ),

        payload=(
            request
            .payload
        ),
        device_key=request.device_key or "",
    )

    charges = (
        request
        .payload
        .get(
            "commission_charges"
        )
    )

    if isinstance(
        charges,
        list,
    ):
        for charge in charges:
            if not isinstance(
                charge,
                dict,
            ):
                continue

            try:
                storage\
                    .record_commission_charge(
                        client_id=(
                            client
                            .id
                        ),

                        charge=(
                            charge
                        ),
                        device_key=request.device_key or "",
                    )

            except Exception as error:
                raise HTTPException(
                    status_code=503,
                    detail="Commission batch was not fully accepted; retry is required",
                ) from error

    control_logs = (
        request
        .payload
        .get(
            "control_logs"
        )
    )

    if isinstance(
        control_logs,
        list,
    ):
        for entry in control_logs:
            if not isinstance(
                entry,
                dict,
            ):
                continue

            try:
                storage\
                    .record_control_log(
                        client_id=(
                            client
                            .id
                        ),

                        entry=(
                            entry
                        ),
                    )

            except Exception as error:
                print(
                    "CONTROL LOG STORE ERROR:",
                    repr(
                        error
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


@app.post(
    "/head/api/clients"
    "/heartbeat"
)
def client_heartbeat(
    request: (
        HeartbeatRequest
    ),

    raw_request: Request,
):
    client = (
        _require_client(
            raw_request
        )
    )

    try:
        storage\
            .upsert_device(
                client_id=(
                    client
                    .id
                ),

                device_key=(
                    request
                    .device_key
                ),

                machine_label=(
                    request
                    .machine_label
                ),
                source_address=raw_request.client.host if raw_request.client else None,
                    software_endpoint=request.software_endpoint,
            )

    except ValueError as error:
        raise HTTPException(
            status_code=400,

            detail=(
                str(
                    error
                )
            ),
        ) from error

    return {
        "status": "ok",

        "server_time": (
            _now_iso()
        ),
    }


@app.post("/head/api/clients/browser-devices")
def client_browser_devices(request: BrowserDevicesRequest, raw_request: Request):
    client = _require_client(raw_request)
    try:
        storage.store_browser_devices(client.id, request.installation_key, request.devices)
    except (ValueError, TypeError) as error:
        raise HTTPException(status_code=400, detail="Invalid browser device activity") from error
    return {"status": "ok"}


@app.get(
    "/head/api/clients"
    "/history"
)
def client_history(
    request: Request,

    limit: int = 20,
):
    client = (
        _require_client(
            request
        )
    )

    if (
        limit
        < 1
    ):
        limit = 1

    if (
        limit
        > 100
    ):
        limit = 100

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
                    client
                    .id
                ),

                limit=(
                    limit
                ),
            )
        ),
    }


@app.get(
    "/head/api/config"
)
def client_config(
    request: Request,
):
    client = (
        _require_client(
            request
        )
    )

    by_platform = (
        storage
        .get_commission_settings(
            client_id=(
                client.id
            ),
        )
    )

    return {
        "commission_default_percent": (
            30
        ),

        "commission": {
            "default_percent": (
                30
            ),

            "by_platform": (
                by_platform
            ),
        },

        "trading": {
            "by_platform": storage.get_trading_settings(),
            "by_asset": storage.get_asset_trading_settings(),
        },

        "version": (
            HEAD_VERSION
        ),
        "entitlements": storage.get_entitlements(client.id),
    }


# ============================================================
# TOPUPS B4 (пополнение баланса ЛК)
# ============================================================

def _parse_topup_amount(
    raw: str,
) -> Decimal:
    try:
        amount = (
            Decimal(
                raw
                .replace(
                    ",",
                    ".",
                )
                .strip()
            )
        )

    except Exception as error:
        raise HTTPException(
            status_code=400,

            detail=(
                "Некорректная "
                "сумма пополнения"
            ),
        ) from error

    if (
        amount
        <= Decimal("0")
    ):
        raise HTTPException(
            status_code=400,

            detail=(
                "Сумма пополнения "
                "должна быть "
                "больше нуля"
            ),
        )

    if (
        amount
        > TOPUP_MAX_AMOUNT
    ):
        raise HTTPException(
            status_code=400,

            detail=(
                "Сумма пополнения "
                "слишком велика"
            ),
        )

    return amount


@app.post(
    "/head/api/clients"
    "/topups",

    status_code=201,
)
def client_topup_create(
    request: (
        ClientTopupRequest
    ),

    raw_request: Request,
):
    client = (
        _require_client(
            raw_request
        )
    )

    amount = (
        _parse_topup_amount(
            request
            .amount
        )
    )

    comment = (
        request
        .comment
        .strip()
    )

    if (
        len(comment)
        > 500
    ):
        comment = (
            comment[
                :500
            ]
        )

    document_name = (
        request
        .document_name
        .strip()

        if (
            request
            .document_name
        )

        else None
    )

    document_mime = (
        request
        .document_mime
        .strip()

        if (
            request
            .document_mime
        )

        else None
    )

    document_data = None

    if (
        request
        .document_base64
    ):
        if (
            not document_name
        ):
            raise HTTPException(
                status_code=400,

                detail=(
                    "Не указано имя "
                    "файла документа"
                ),
            )

        try:
            decoded = (
                base64
                .b64decode(
                    request
                    .document_base64,

                    validate=(
                        True
                    ),
                )
            )

        except Exception as error:
            raise HTTPException(
                status_code=400,

                detail=(
                    "Некорректные "
                    "данные документа"
                ),
            ) from error

        if (
            len(decoded)
            > (
                TOPUP_MAX_DOCUMENT_BYTES
            )
        ):
            raise HTTPException(
                status_code=400,

                detail=(
                    "Документ больше "
                    "8 МБ"
                ),
            )

        if (
            not document_mime
        ):
            document_mime = (
                "application/"
                "octet-stream"
            )

        document_data = (
            request
            .document_base64
        )

    created = (
        storage
        .create_topup_request(
            client_id=(
                client.id
            ),

            amount=(
                amount
            ),

            comment=(
                comment
            ),

            document_name=(
                document_name
            ),

            document_mime=(
                document_mime
            ),

            document_data=(
                document_data
            ),
        )
    )

    return {
        "request": (
            created
        ),
    }


@app.get(
    "/head/api/clients"
    "/topups"
)
def client_topups(
    request: Request,
):
    client = (
        _require_client(
            request
        )
    )

    return {
        "requests": (
            storage
            .list_topup_requests(
                client_id=(
                    client
                    .id
                ),

                limit=50,
            )
        ),

        "balance": (
            str(
                storage
                .get_commission_balance(
                    client
                    .id
                )
            )
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

                "entitlements": storage.get_entitlements(client.id),
                "paid_commissions": str(sum(
                    (Decimal(charge["amount"]) for charge in storage.list_commission_charges(client.id, limit=1000000)
                     if Decimal(charge["amount"]) > 0 and charge["broker"] != "admin_adjustment"), Decimal("0"),
                )),
                "cabinet_balance": (
                    str(
                        storage
                        .get_commission_balance(
                            client.id
                        )
                    )
                ),
            }

            for client
            in clients
        ],
    }


@app.get(
    "/head/api/admin/clients"
    "/{client_id}/profile"
)
def admin_client_profile(
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
            detail="Client not found",
        )

    accounts = []

    if (
        client
        .latest_payload
    ):
        try:
            import json

            payload = (
                json
                .loads(
                    client
                    .latest_payload
                )
            )

            if isinstance(
                payload,
                dict,
            ):
                incoming = (
                    payload
                    .get(
                        "accounts",
                        [],
                    )
                )

                if isinstance(
                    incoming,
                    list,
                ):
                    accounts = [
                        {
                            key: (
                                account
                                .get(key)
                            )

                            for key
                            in (
                                "id",
                                "name",
                                "broker",
                                "broker_account_id",
                                "mode",
                                "enabled",
                                "net_deposits",
                                "historical_balance",
                                "realized_profit",
                                "unrealized_profit",
                                "roe_percent",
                                "roi_percent",
                            )
                        }

                        for account
                        in incoming
                        if isinstance(
                            account,
                            dict,
                        )
                    ]

        except (
            ValueError,
            TypeError,
        ):
            pass

    return {
        "client": (
            _client_dict(
                client
            )
        ),
        "cabinet_balance": (
            str(
                storage
                .get_commission_balance(
                    client_id
                ))
        ),
        "accounts": (
            accounts
        ),
        "commission_settings": (
            storage
            .get_commission_settings(
                client_id
            )
        ),
        "default_percent": 30,
    }


@app.get(
    "/head/api/admin"
    "/overview"
)
def admin_overview(
    request: Request,

    days: int = 7,
    all_time: bool = False,
):
    _require_admin(
        request
    )

    if (
        days
        < 1
    ):
        days = 1

    if (
        days
        > 180
    ):
        days = 180

    return {
        "stats": (
            storage
            .overview_stats()
        ),

        "daily": (
            storage
            .daily_activity(
                days=days,
                all_time=all_time,
            )
        ),

        "events": (
            storage
            .list_activity_events(
                limit=50,
            )
        ),
    }


@app.get(
    "/head/api/admin/devices"
)
def admin_devices(
    request: Request,
):
    _require_admin(
        request
    )

    from datetime import (
        datetime,
        timezone,
    )

    clients_by_id = {
        client.id: client
        for client
        in storage
        .list_clients()
    }

    now = (
        datetime
        .now(
            timezone.utc
        )
    )

    devices = []

    for device in (
        storage
        .list_devices()
    ):
        client = (
            clients_by_id
            .get(
                device[
                    "client_id"
                ],
            )
        )

        online = False

        try:
            last_seen = (
                datetime
                .fromisoformat(
                    device[
                        "last_seen_at"
                    ]
                )
            )

            online = (
                (
                    now
                    - last_seen
                )
                .total_seconds()
                <= (
                    DEVICE_ONLINE_SECONDS
                )
            )

        except Exception:
            online = False

        (
            devices
            .append(
                {
                    **(
                        device
                    ),

                    "online": (
                        online
                    ),

                    "client_login": (
                        client
                        .login

                        if (
                            client
                            is not None
                        )

                        else None
                    ),

                    "client_full_name": (
                        client
                        .full_name

                        if (
                            client
                            is not None
                        )

                        else None
                    ),
                }
            )
        )

    return {
        "devices": devices,
        "online_seconds": DEVICE_ONLINE_SECONDS,
        "browser_devices": [
            {**device, "online": (now - datetime.fromisoformat(device["last_seen_at"])).total_seconds() <= DEVICE_ONLINE_SECONDS}
            for device in storage.list_browser_devices()
        ],
    }


@app.get(
    "/head/api/admin"
    "/activity"
)
def admin_activity(
    request: Request,
):
    _require_admin(
        request
    )

    devices = (
        admin_devices(
            request
        )["devices"]
    )

    clients = {
        client.id: client
        for client in (
            storage
            .list_clients()
        )
    }

    online_by_client: dict[int, list[dict]] = {}

    for device in devices:
        if (
            device["online"]
        ):
            online_by_client.setdefault(
                device["client_id"],
                [],
            ).append(
                device
            )

    users = [
        {
            "client": (
                _client_dict(
                    clients[client_id]
                )
            ),
            "online_devices": (
                len(
                    active_devices
                )
            ),
            "devices": (
                sorted(
                    active_devices,
                    key=lambda item: (
                        item[
                            "last_seen_at"
                        ]
                    ),
                    reverse=True,
                )
            ),
        }

        for client_id, active_devices
        in online_by_client.items()
        if client_id in clients
    ]

    return {
        "users": (
            sorted(
                users,
                key=lambda item: (
                    item[
                        "client"
                    ]["login"]
                ),
            )
        ),
        "online_seconds": (
            DEVICE_ONLINE_SECONDS
        ),
    }


@app.post(
    "/head/api/admin/devices"
    "/{device_id}/head"
)
def admin_device_set_head(
    device_id: int,

    request: (
        AdminDeviceHeadRequest
    ),

    raw_request: Request,
):
    _require_admin(
        raw_request
    )

    devices = {
        device[
            "id"
        ]: device

        for device
        in storage
        .list_devices()
    }

    if (
        device_id
        not in devices
    ):
        raise HTTPException(
            status_code=404,

            detail=(
                "Device not found"
            ),
        )

    storage\
        .set_device_head_flag(
            device_id=(
                device_id
            ),

            is_head=(
                request
                .is_head
            ),
        )

    return {
        "status": "ok"
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


@app.post("/head/api/admin/clients/{client_id}/balance")
def admin_balance_set(client_id: int, payload: AdminBalanceRequest, request: Request):
    _require_admin(request)
    if storage.get_client_by_id(client_id) is None:
        raise HTTPException(status_code=404, detail="Client not found")
    try:
        balance = Decimal(payload.balance.strip().replace(",", "."))
        if not balance.is_finite() or abs(balance) > TOPUP_MAX_AMOUNT:
            raise ValueError("Invalid balance")
        return {"entitlements": storage.adjust_cabinet_balance(client_id, balance, payload.note)}
    except (ValueError, ArithmeticError) as error:
        raise HTTPException(status_code=400, detail="Invalid balance") from error


@app.post("/head/api/admin/clients/{client_id}/permissions")
def admin_permissions_set(client_id: int, payload: AdminPermissionsRequest, request: Request):
    _require_admin(request)
    if storage.get_client_by_id(client_id) is None:
        raise HTTPException(status_code=404, detail="Client not found")
    return {"entitlements": storage.set_insufficient_balance_permission(client_id, payload.allow_insufficient_balance)}


@app.get("/head/api/admin/asset-trading-settings")
def admin_asset_trading_settings(request: Request):
    _require_admin(request)
    return {"by_asset": storage.get_asset_trading_settings()}


@app.post("/head/api/admin/asset-trading-settings")
def admin_asset_trading_settings_set(settings: AdminAssetTradingSettingsRequest, request: Request):
    _require_admin(request)
    platform = settings.platform.strip().lower()
    ticker = settings.ticker.strip().upper()
    if not platform or not platform.replace("_", "").isalnum() or not ticker or len(ticker) > 64:
        raise HTTPException(status_code=400, detail="Invalid platform or asset")
    values: dict[str, Decimal | None] = {}
    for field in ("min_profit_percent", "entry_rebound_percent", "trailing_percent", "take_profit_percent", "max_take_profit_percent", "order_amount_multiplier", "max_order_amount_multiplier"):
        raw = getattr(settings, field)
        if raw is None or not raw.strip():
            values[field] = None
            continue
        try:
            number = Decimal(raw.strip().replace(",", "."))
        except Exception as error:
            raise HTTPException(status_code=400, detail=f"Invalid {field}") from error
        if not number.is_finite() or not 0 < number <= 100 or (field.endswith("_multiplier") and number < 1):
            raise HTTPException(status_code=400, detail=f"Invalid {field}")
        values[field] = number
    storage.set_asset_trading_settings(platform, ticker, **values)
    return {"by_asset": storage.get_asset_trading_settings()}


@app.get("/head/api/admin/trading-settings")
def admin_trading_settings(request: Request):
    _require_admin(request)
    return {"by_platform": storage.get_trading_settings()}


@app.post("/head/api/admin/trading-settings")
def admin_trading_settings_set(
    settings: AdminTradingSettingsRequest,
    request: Request,
):
    _require_admin(request)
    platform = settings.platform.strip().lower()
    if platform not in {"tinvest", "bybit"}:
        raise HTTPException(status_code=400, detail="Unknown platform")

    values = {}
    for field in (
        "min_profit_percent",
        "entry_rebound_percent",
        "trailing_percent",
    ):
        try:
            value = Decimal(getattr(settings, field).strip().replace(",", "."))
        except Exception as error:
            raise HTTPException(status_code=400, detail=f"Invalid {field}") from error
        if not value.is_finite() or value <= 0 or value > 100:
            raise HTTPException(status_code=400, detail=f"Invalid {field}")
        values[field] = value

    storage.set_trading_settings(platform=platform, **values)
    return {"by_platform": storage.get_trading_settings()}


@app.get(
    "/head/api/admin/commission"
)
def admin_commission(
    request: Request,
):
    _require_admin(
        request
    )

    settings = (
        storage
        .list_commission_settings()
    )

    balances = {
        client_id: (
            str(
                storage
                .get_commission_balance(
                    client_id
                )
            )
        )

        for client_id
        in {
            item[
                "client_id"
            ]

            for item
            in settings
        }
    }

    return {
        "settings": (
            settings
        ),

        "balances": (
            balances
        ),

        "default_percent": (
            30
        ),
    }


@app.post(
    "/head/api/admin/commission"
)
def admin_commission_set(
    request: (
        AdminCommissionSetRequest
    ),

    raw_request: Request,
):
    _require_admin(
        raw_request
    )

    platform = (
        request
        .platform
        .strip()
        .lower()
    )

    if not platform:
        raise HTTPException(
            status_code=400,

            detail=(
                "Platform is required"
            ),
        )

    try:
        percent = (
            Decimal(
                request
                .percent
                .replace(
                    ",",
                    ".",
                )
            )
        )

    except Exception as error:
        raise HTTPException(
            status_code=400,

            detail=(
                "Invalid percent value"
            ),
        ) from error

    if (
        percent
        < Decimal("0")
        or (
            percent
            > Decimal(
                "100"
            )
        )
    ):
        raise HTTPException(
            status_code=400,

            detail=(
                "Percent must be "
                "between 0 and 100"
            ),
        )

    client = (
        storage
        .get_client_by_id(
            request
            .client_id
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

    storage\
        .set_commission_percent(
            client_id=(
                request
                .client_id
            ),

            platform=(
                platform
            ),

            percent=(
                percent
            ),
        )

    return {
        "status": "ok",

        "client_id": (
            request
            .client_id
        ),

        "platform": (
            platform
        ),

        "percent": (
            str(
                percent
            )
        ),
    }


@app.post(
    "/head/api/admin/clients/"
    "{client_id}/reset-password"
)
def admin_client_reset_password(
    client_id: int,

    raw_request: Request,
):
    _require_admin(
        raw_request
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

    code, expires_at = (
        storage
        .set_password_reset_code(
            client_id=(
                client_id
            ),

            ttl_seconds=(
                RESET_CODE_TTL_SECONDS
            ),
        )
    )

    return {
        "status": "ok",

        "client_id": (
            client_id
        ),

        "login": (
            client
            .login
        ),

        "reset_code": (
            code
        ),

        "expires_at": (
            expires_at
        ),
    }


@app.get(
    "/head/api/admin/commission/charges"
)
def admin_commission_charges(
    request: Request,

    client_id: (
        int | None
    ) = None,

    limit: int = 100,
):
    _require_admin(
        request
    )

    if limit < 1:
        limit = 1

    if limit > 1000:
        limit = 1000

    charges = (
        storage
        .list_commission_charges(
            client_id=(
                client_id
            ),

            limit=(
                limit
            ),
        )
    )

    balance = (
        str(
            storage
            .get_commission_balance(
                client_id
            )
        )

        if (
            client_id
            is not None
        )

        else None
    )

    return {
        "charges": (
            charges
        ),

        "balance": (
            balance
        ),
    }


@app.get(
    "/head/api/admin"
    "/control-logs"
)
def admin_control_logs(
    request: Request,

    client_id: (
        int | None
    ) = None,

    limit: int = 100,
):
    _require_admin(
        request
    )

    if limit < 1:
        limit = 1

    if limit > 1000:
        limit = 1000

    logs = (
        storage
        .list_control_logs(
            client_id=(
                client_id
            ),

            limit=(
                limit
            ),
        )
    )

    return {
        "control_logs": (
            logs
        ),
    }


@app.get(
    "/head/api/admin"
    "/topups"
)
def admin_topups(
    request: Request,

    status: (
        str | None
    ) = None,

    client_id: (
        int | None
    ) = None,

    limit: int = 100,
):
    _require_admin(
        request
    )

    if limit < 1:
        limit = 1

    if limit > 1000:
        limit = 1000

    clients_by_id = {
        client.id: client

        for client
        in storage
        .list_clients()
    }

    items = []

    for item in (
        storage
        .list_topup_requests(
            client_id=(
                client_id
            ),

            status=(
                status
            ),

            limit=(
                limit
            ),
        )
    ):
        client = (
            clients_by_id
            .get(
                item[
                    "client_id"
                ],
            )
        )

        items.append(
            {
                **(
                    item
                ),

                "client_login": (
                    client
                    .login

                    if (
                        client
                        is not None
                    )

                    else None
                ),

                "client_full_name": (
                    client
                    .full_name

                    if (
                        client
                        is not None
                    )

                    else None
                ),
            }
        )

    pending_count = (
        len(
            storage
            .list_topup_requests(
                status=(
                    "pending"
                ),

                limit=(
                    1000
                ),
            )
        )
    )

    return {
        "requests": (
            items
        ),

        "pending_count": (
            pending_count
        ),
    }


@app.get(
    "/head/api/admin"
    "/topups"
    "/{request_id}/document"
)
def admin_topup_document(
    request_id: int,

    request: Request,
):
    _require_admin(
        request
    )

    item = (
        storage
        .get_topup_request(
            request_id,

            with_document=(
                True
            ),
        )
    )

    if (
        item
        is None
    ):
        raise HTTPException(
            status_code=404,

            detail=(
                "Заявка не найдена"
            ),
        )

    data = (
        item
        .get(
            "document_data"
        )
    )

    if (
        not data
    ):
        raise HTTPException(
            status_code=404,

            detail=(
                "К заявке не "
                "приложен документ"
            ),
        )

    try:
        decoded = (
            base64
            .b64decode(
                data
            )
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,

            detail=(
                "Не удалось "
                "прочитать документ"
            ),
        ) from error

    media_type = (
        item
        .get(
            "document_mime"
        )

        or (
            "application/"
            "octet-stream"
        )
    )

    filename = (
        item
        .get(
            "document_name"
        )

        or (
            "topup-"
            + str(
                request_id
            )
        )
    )

    return Response(
        content=(
            decoded
        ),

        media_type=(
            media_type
        ),

        headers={
            "Content-Disposition": (
                "inline; "
                "filename*="
                "UTF-8''"
                + quote(
                    filename
                )
            ),
        },
    )


def _review_topup(
    request_id: int,

    review: (
        AdminTopupReviewRequest
    ),

    raw_request: Request,

    action: str,
) -> dict:
    _require_admin(
        raw_request
    )

    try:
        if (
            action
            == "approve"
        ):
            item = (
                storage
                .approve_topup_request(
                    request_id,

                    review_note=(
                        review
                        .review_note
                    ),
                )
            )

        else:
            item = (
                storage
                .reject_topup_request(
                    request_id,

                    review_note=(
                        review
                        .review_note
                    ),
                )
            )

    except ValueError as error:
        raise HTTPException(
            status_code=409,

            detail=str(
                error
            ),
        ) from error

    if (
        item
        is None
    ):
        raise HTTPException(
            status_code=404,

            detail=(
                "Заявка не найдена"
            ),
        )

    balance = (
        str(
            storage
            .get_commission_balance(
                item[
                    "client_id"
                ]
            )
        )
    )

    return {
        "status": (
            "ok"
        ),

        "request": (
            item
        ),

        "balance": (
            balance
        ),
    }


@app.post(
    "/head/api/admin"
    "/topups"
    "/{request_id}/approve"
)
def admin_topup_approve(
    request_id: int,

    request: (
        AdminTopupReviewRequest
    ),

    raw_request: Request,
):
    return (
        _review_topup(
            request_id,

            review=(
                request
            ),

            raw_request=(
                raw_request
            ),

            action=(
                "approve"
            ),
        )
    )


@app.post(
    "/head/api/admin"
    "/topups"
    "/{request_id}/reject"
)
def admin_topup_reject(
    request_id: int,

    request: (
        AdminTopupReviewRequest
    ),

    raw_request: Request,
):
    return (
        _review_topup(
            request_id,

            review=(
                request
            ),

            raw_request=(
                raw_request
            ),

            action=(
                "reject"
            ),
        )
    )


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
