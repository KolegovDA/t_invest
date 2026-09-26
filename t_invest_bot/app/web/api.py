from __future__ import annotations

import hashlib
import json
import os
import re
import threading

from contextlib import asynccontextmanager
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from decimal import Decimal, ROUND_HALF_UP

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
    JSONResponse,
)
from pydantic import (
    BaseModel,
)

from notifications.telegram_notifier import (
    TelegramNotifier,
)

from application.live_account_service import (
    LiveAccountService,
)
from application.account_performance_service import (
    AccountPerformanceService,
)

from application.auth_service import (
    AuthService,
)

from application.head_server_client import (
    HeadReplicationWorker,
    HeadServerClient,
    HeadSyncPayloadBuilder,
)

from application.auto_rebalance_service import (
    AutoRebalanceService,
)
from application.auto_portfolio_selector import (
    AutoPortfolioSelector,
    IndexPortfolioSelector,
    InstrumentMarketSnapshot,
)
from application.index_presets import (
    AUTO_UNIVERSE_TICKERS,
    INDEX_PRESETS,
    find_index_preset,
)
from application.instrument_catalog_service import (
    InstrumentCatalogService,
)
from application.instrument_market_service import (
    InstrumentMarketService,
)
from application.live_start_validation_service import (
    LiveStartValidationService,
)
from application.knowledge_engine import (
    KnowledgeEngine,
)
from application.multi_instrument_session_config import (
    InstrumentConfig,
    MultiInstrumentSessionConfig,
)
from application.multi_instrument_trading_session_factory import (
    MultiInstrumentTradingSessionFactory,
)
from application.operation_log_service import (
    OperationLogService,
)

from application.phantom_position_auditor import (
    PhantomPositionAuditor,
)
from application.portfolio_orchestrator import (
    PortfolioOrchestrator,
)
from application.reconciliation_journal import (
    ReconciliationJournal,
)
from application.sandbox_session_registry import (
    SandboxSessionSnapshot,
    sandbox_session_registry,
)
from application.session_instrument_manager import (
    SessionInstrumentManager,
)
from application.trading_account_service import (
    TradingAccountCredentials,
    TradingAccountService,
)
from application.trading_mode_guard import (
    TradingModeGuard,
)
from application.trading_session_state_service import (
    TradingSessionStateService,
)
from application.web_runner_recovery_service import (
    WebRunnerRecoveryService,
)
from application.web_runner_registry import (
    web_runner_registry,
)
from application.web_runner_service import (
    WebRunnerService,
)

from config.runtime_paths import (
    get_database_path,
)
from config.settings import (
    Settings,
)

from domain.money_movement import (
    MoneyMovement,
)
from domain.trading_account import (
    BrokerType,
    CommissionMode,
    TradingAccount,
    TradingAccountMode,
)

from infrastructure.brokers.default_registry import (
    create_default_broker_registry,
)
from infrastructure.security.dpapi_secret_protector import (
    DPAPISecretProtector,
)
from infrastructure.sqlite.api_usage_repository import (
    SQLiteApiUsageRepository,
)
from infrastructure.sqlite.instrument_statistics_repository import (
    SQLiteInstrumentStatisticsRepository,
)
from infrastructure.sqlite.money_movement_repository import (
    SQLiteMoneyMovementRepository,
)
from infrastructure.sqlite.operation_log_repository import (
    SQLiteOperationLogRepository,
)
from infrastructure.sqlite.reconciliation_event_repository import (
    SQLiteReconciliationEventRepository,
)
from infrastructure.sqlite.sqlite_database import (
    SQLiteDatabase,
)
from infrastructure.sqlite.user_repository import (
    SQLiteUserRepository,
)
from infrastructure.tinvest.candles_mapper import (
    TInvestCandlesMapper,
)
from infrastructure.tinvest.client_factory import (
    TInvestClientFactory,
)
from infrastructure.tinvest.history_provider import (
    TInvestHistoryProvider,
)
from infrastructure.tinvest.live_position_provider import (
    TInvestLivePositionProvider,
)
from infrastructure.sqlite.trading_account_repository import (
    TradingAccountRepository,
)
from infrastructure.sqlite.trading_state_repository import (
    TradingStateRepository,
)
from infrastructure.sqlite.web_session_repository import (
    SQLiteWebSessionRepository,
)

from web.session_registry import (
    WebSession,
    session_registry,
)


APP_VERSION = "1.2.0-dev"


settings = Settings.from_env()


# ============================================================
# DATABASE
# ============================================================

database_path = (
    get_database_path()
)


database = SQLiteDatabase(
    database_path=(
        database_path
    ),
)

database.initialize()


print(
    "DATABASE PATH:",
    database_path,
)


# ============================================================
# WEB SESSION REPOSITORY
# ============================================================

session_registry.repository = (
    SQLiteWebSessionRepository(
        database=database,
    )
)

session_registry.load_from_repository()


# ============================================================
# API USAGE REPOSITORY
# ============================================================

api_usage_repository = (
    SQLiteApiUsageRepository(
        database=database,
    )
)


# ============================================================
# RECONCILIATION JOURNAL 1.1
# ============================================================

reconciliation_event_repository = (
    SQLiteReconciliationEventRepository(
        database=database,
    )
)


reconciliation_journal = (
    ReconciliationJournal(
        repository=(
            reconciliation_event_repository
        ),
    )
)


# ============================================================
# OPERATION LOG 1.2
# ============================================================

operation_log_repository = (
    SQLiteOperationLogRepository(
        database=database,
    )
)


operation_log_service = (
    OperationLogService(
        repository=(
            operation_log_repository
        ),
    )
)


# ============================================================
# MONEY MOVEMENTS + PERFORMANCE 1.2 (пп. 4-5)
# ============================================================

money_movement_repository = (
    SQLiteMoneyMovementRepository(
        database=database,
    )
)


# ============================================================
# KNOWLEDGE ENGINE 1.1
# ============================================================

instrument_statistics_repository = (
    SQLiteInstrumentStatisticsRepository(
        database=database,
    )
)


knowledge_engine = (
    KnowledgeEngine(
        repository=(
            instrument_statistics_repository
        ),
    )
)


# ============================================================
# TRADING STATE 1.1
# ============================================================

trading_state_repository = (
    TradingStateRepository(
        db_path=str(
            database_path
        ),
    )
)


trading_state_service = (
    TradingSessionStateService(
        repository=(
            trading_state_repository
        ),

        operation_log=(
            operation_log_service
        ),
    )
)


phantom_position_auditor = (
    PhantomPositionAuditor()
)


account_performance_service = (
    AccountPerformanceService(
        movement_repository=(
            money_movement_repository
        ),

        state_repository=(
            trading_state_repository
        ),
    )
)


# ============================================================
# AUTH + HEAD SERVER 1.2
# ============================================================

user_repository = (
    SQLiteUserRepository(
        db_path=str(
            database_path
        ),
    )
)


auth_service = (
    AuthService(
        repository=(
            user_repository
        ),
    )
)


head_server_client = (
    HeadServerClient(
        base_url=(
            settings
            .head_server_url
        ),
    )

    if (
        settings
        .head_server_enabled

        and (
            settings
            .head_server_url
        )
    )

    else None
)


def _register_user_on_head(
    user_id: int,
) -> None:
    """
    Best-effort регистрация
    на головном сервере
    (7.3). Ошибки не влияют
    на клиента.
    """

    if (
        head_server_client
        is None
    ):
        return

    def _run() -> None:
        try:
            stored = (
                user_repository
                .get_user_by_id(
                    user_id
                )
            )

            if (
                stored
                is None
            ):
                return

            result = (
                head_server_client
                .register_user(
                    stored_user=(
                        stored
                    ),
                )
            )

            if (
                result
                is None
            ):
                return

            api_key = (
                result
                .get(
                    "api_key"
                )
            )

            if api_key:
                user_repository\
                    .set_user_head_api_key(
                        user_id=(
                            user_id
                        ),

                        api_key=(
                            str(
                                api_key
                            )
                        ),
                    )

                head_replication_worker\
                    .sync_now()

        except Exception as error:
            print(
                "HEAD REGISTER ERROR:",
                repr(
                    error
                ),
            )

    threading.Thread(
        target=(
            _run
        ),

        daemon=(
            True
        ),
    ).start()


def _login_user_on_head(
    user_id: int,
) -> None:
    """
    Best-effort связка
    с головным сервером
    при входе: получает
    api_key, если
    регистрации ещё
    не было.
    """

    if (
        head_server_client
        is None
    ):
        return

    def _run() -> None:
        try:
            stored = (
                user_repository
                .get_user_by_id(
                    user_id
                )
            )

            if (
                stored
                is None

                or (
                    stored
                    .head_api_key
                )
            ):
                return

            api_key = (
                head_server_client
                .login_user(
                    login=(
                        stored
                        .login
                    ),

                    password_hash=(
                        stored
                        .password_hash
                    ),
                )
            )

            if api_key:
                user_repository\
                    .set_user_head_api_key(
                        user_id=(
                            user_id
                        ),

                        api_key=(
                            api_key
                        ),
                    )

        except Exception as error:
            print(
                "HEAD LOGIN ERROR:",
                repr(
                    error
                ),
            )

    threading.Thread(
        target=(
            _run
        ),

        daemon=(
            True
        ),
    ).start()


# ============================================================
# TRADING ACCOUNTS 1.1
# ============================================================

trading_account_repository = (
    TradingAccountRepository(
        db_path=str(
            database_path
        ),
    )
)


trading_account_service = (
    TradingAccountService(
        repository=(
            trading_account_repository
        ),

        secret_protector=(
            DPAPISecretProtector()
        ),
    )
)


head_sync_payload_builder = (
    HeadSyncPayloadBuilder(
        trading_account_service=(
            trading_account_service
        ),

        trading_state_repository=(
            trading_state_repository
        ),

        account_performance_service=(
            account_performance_service
        ),

        operation_log_repository=(
            operation_log_repository
        ),
    )
)


head_replication_worker = (
    HeadReplicationWorker(
        client=(
            head_server_client
        ),

        payload_builder=(
            head_sync_payload_builder
        ),

        user_repository=(
            user_repository
        ),
    )
)


# ============================================================
# BROKER REGISTRY
# ============================================================

broker_registry = (
    create_default_broker_registry()
)


# ============================================================
# PUSH NOTIFICATIONS 1.2 (п. 3)
# ============================================================

#
# Канал по умолчанию — Telegram:
# TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID
# в настройках сервера. Не заданы —
# уведомления отключены.
#
telegram_notifier = (
    TelegramNotifier(
        bot_token=(
            settings
            .telegram_bot_token
        ),

        chat_id=(
            settings
            .telegram_chat_id
        ),
    )

    if (
        settings
        .telegram_bot_token

        and (
            settings
            .telegram_chat_id
        )
    )

    else None
)


# ============================================================
# LIVE VALIDATION 1.1
# ============================================================

live_start_validation_service = (
    LiveStartValidationService(
        trading_account_service=(
            trading_account_service
        ),

        broker_registry=(
            broker_registry
        ),

        session_factory=(
            MultiInstrumentTradingSessionFactory(
                settings=settings,
                knowledge_engine=(
                    knowledge_engine
                ),

                operation_log=(
                    operation_log_service
                ),

                notifier=(
                    telegram_notifier
                ),
            )
        ),

        portfolio_orchestrator=(
            PortfolioOrchestrator()
        ),
    )
)


# ============================================================
# INSTRUMENT CATALOG 1.1
# ============================================================

instrument_catalog_service = (
    InstrumentCatalogService(
        settings=settings,
        trading_account_service=(
            trading_account_service
        ),
    )
)


instrument_market_service = (
    InstrumentMarketService(
        settings=settings,
        trading_account_service=(
            trading_account_service
        ),
    )
)


# ============================================================
# RUNNER RECOVERY 1.1
# ============================================================

web_runner_recovery_service = (
    WebRunnerRecoveryService(
        settings=settings,
        state_repository=(
            trading_state_repository
        ),
        state_service=(
            trading_state_service
        ),
        trading_account_service=(
            trading_account_service
        ),
        runner_registry=(
            web_runner_registry
        ),
        api_usage_repository=(
            api_usage_repository
        ),
        reconciliation_journal=(
            reconciliation_journal
        ),
        polling_interval_seconds=10,
    )
)


# ============================================================
# FASTAPI
# ============================================================

@asynccontextmanager
async def app_lifespan(
    _app: FastAPI,
):
    # Startup recovery is part of the normal application lifecycle.
    # We intentionally do not mark runners STOPPED on application
    # shutdown: RUNNING/DRAINING snapshots must survive an exe restart.
    if not os.getenv(
        "PYTEST_CURRENT_TEST"
    ):
        (
            web_runner_recovery_service
            .recover_active_runners()
        )

        if (
            head_server_client
            is not None
        ):
            #
            # 7.3: фоновая
            # репликация в
            # головной сервер.
            #
            head_replication_worker\
                .start()

    yield


app = FastAPI(
    title="ESM Trade System API",
    version=APP_VERSION,
    lifespan=app_lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# AUTH 1.2 (п. 6): регистрация, вход, PIN, биометрия
# ============================================================

AUTH_COOKIE = (
    "esm_auth"
)


AUTH_EXEMPT_PATHS = {
    "/api/auth/status",
    "/api/auth/register",
    "/api/auth/login",
    "/api/auth/pin/verify",
    "/api/auth/biometric/verify",
    "/api/health",
    "/api/version",
}


def _auth_is_enforced() -> bool:
    #
    # До первой регистрации
    # приложение открыто;
    # в тестах авторизация
    # не проверяется.
    #
    if (
        os.getenv(
            "PYTEST_CURRENT_TEST"
        )
    ):
        return False

    try:
        return (
            auth_service
            .has_users()
        )

    except Exception:
        return False


def _token_from_request(
    request,
) -> str | None:
    token = (
        request
        .cookies
        .get(
            AUTH_COOKIE
        )
    )

    if token:
        return token

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
        return (
            authorization[
                7:
            ]
        )

    return None


@app.middleware(
    "http"
)
async def auth_middleware(
    request,
    call_next,
):
    path = (
        request
        .url
        .path
    )

    if (
        path.startswith(
            "/api"
        )

        and (
            path
            not in (
                AUTH_EXEMPT_PATHS
            )
        )

        and (
            _auth_is_enforced()
        )
    ):
        token = (
            _token_from_request(
                request
            )
        )

        user = (
            auth_service
            .get_user_by_token(
                token
            )

            if token

            else None
        )

        if (
            user
            is None
        ):
            return (
                JSONResponse(
                    status_code=(
                        401
                    ),

                    content={
                        "detail": (
                            "Требуется "
                            "авторизация"
                        ),
                    },
                )
            )

        (
            request
            .state
            .auth_user
        ) = (
            user
        )

    return (
        await (
            call_next(
                request
            )
        )
    )


# ============================================================
# REQUEST MODELS
# ============================================================

class StartPlanInstrumentRequest(
    BaseModel
):
    ticker: str
    levels: int
    quantity: int


class StartPlanRequest(
    BaseModel
):
    available_cash: (
        Decimal | None
    ) = None

    trading_account_id: (
        str | None
    ) = None

    instruments: list[
        StartPlanInstrumentRequest
    ]


class StartSandboxRequest(
    BaseModel
):
    force: bool = False

    trading_account_id: (
        str | None
    ) = None

    instruments: list[
        StartPlanInstrumentRequest
    ]

    auto_rebalance: bool = (
        False
    )

    max_instruments: int = 5

    max_price: (
        Decimal | None
    ) = None


class PhantomResolveItem(
    BaseModel
):
    session_id: str

    instrument_uids: list[
        str
    ]


class PhantomResolveRequest(
    BaseModel
):
    items: list[
        PhantomResolveItem
    ]


class AddMoneyMovementRequest(
    BaseModel
):
    amount: Decimal

    note: str = ""


class RegisterRequest(
    BaseModel
):
    full_name: str

    phone: str

    email: str

    birth_date: str

    login: str

    password: str

    device_id: str = (
        "web"
    )


class LoginRequest(
    BaseModel
):
    login: str

    password: str

    device_id: str = (
        "web"
    )


class AuthStatusRequest(
    BaseModel
):
    device_id: str = (
        "web"
    )


class PinSetRequest(
    BaseModel
):
    device_id: str

    pin: str


class PinVerifyRequest(
    BaseModel
):
    device_id: str

    pin: str


class BiometricRegisterRequest(
    BaseModel
):
    device_id: str

    credential_id: str


class BiometricVerifyRequest(
    BaseModel
):
    device_id: str

    credential_id: str


class CreateTradingAccountRequest(
    BaseModel
):
    name: str

    broker: BrokerType = (
        BrokerType.TINVEST
    )

    broker_account_id: str

    credentials: dict[
        str,
        str,
    ]

    mode: TradingAccountMode = (
        TradingAccountMode.LIVE
    )

    commission_mode: CommissionMode = (
        CommissionMode.AUTO
    )

    custom_buy_commission_percent: (
        Decimal | None
    ) = None

    custom_sell_commission_percent: (
        Decimal | None
    ) = None

    enabled: bool = True


class UpdateTradingAccountRequest(
    BaseModel
):
    name: (
        str | None
    ) = None

    broker: (
        BrokerType | None
    ) = None

    broker_account_id: (
        str | None
    ) = None

    credentials: (
        dict[str, str]
        | None
    ) = None

    mode: (
        TradingAccountMode
        | None
    ) = None

    commission_mode: (
        CommissionMode
        | None
    ) = None

    custom_buy_commission_percent: (
        Decimal | None
    ) = None

    custom_sell_commission_percent: (
        Decimal | None
    ) = None

    enabled: (
        bool | None
    ) = None


class DiscoverBrokerAccountsRequest(
    BaseModel
):
    broker: BrokerType = (
        BrokerType.TINVEST
    )

    credentials: dict[
        str,
        str,
    ]

    mode: TradingAccountMode = (
        TradingAccountMode.LIVE
    )


# ============================================================
# BROKERS
# ============================================================

@app.get(
    "/api/brokers"
)
def get_brokers():
    supported = set(
        broker_registry
        .get_supported_brokers()
    )

    return {
        "brokers": [
            _build_broker_info(
                broker=broker,

                supported=(
                    broker
                    in supported
                ),
            )
            for broker
            in BrokerType
        ],
    }


# ============================================================
# ACCOUNTS
# ============================================================

@app.get(
    "/api/accounts"
)
def get_trading_accounts():
    accounts = (
        trading_account_service
        .get_all()
    )

    return {
        "accounts": [
            _trading_account_to_dict(
                account
            )
            for account
            in accounts
        ],
    }


@app.get(
    "/api/accounts/{account_id}"
)
def get_trading_account(
    account_id: str,
):
    try:
        account = (
            trading_account_service
            .get(
                account_id
            )
        )

    except KeyError as error:
        raise HTTPException(
            status_code=404,
            detail="Trading account not found",
        ) from error

    return (
        _trading_account_to_dict(
            account
        )
    )


@app.post(
    "/api/accounts",
    status_code=201,
)
def create_trading_account(
    request: CreateTradingAccountRequest,
):
    if not (
        broker_registry
        .is_supported(
            request.broker
        )
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Broker is not supported yet: "
                f"{request.broker.value}"
            ),
        )

    try:
        account = (
            trading_account_service
            .create(
                name=request.name,

                broker=request.broker,

                broker_account_id=(
                    request
                    .broker_account_id
                ),

                credentials=(
                    request.credentials
                ),

                mode=request.mode,

                commission_mode=(
                    request
                    .commission_mode
                ),

                custom_buy_commission_percent=(
                    request
                    .custom_buy_commission_percent
                ),

                custom_sell_commission_percent=(
                    request
                    .custom_sell_commission_percent
                ),

                enabled=request.enabled,
            )
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(
                error
            ),
        ) from error

    api_usage_repository.record(
        source="web",
        operation=(
            "trading_account_created"
        ),
        weight=1,
    )

    operation_log_service.record(
        event_type=(
            "ACCOUNT_ADDED"
        ),

        trading_account_id=(
            account.id
        ),

        details=(
            "name="
            f"{account.name} "

            "broker="
            f"{account.broker.value} "

            "mode="
            f"{account.mode.value}"
        ),
    )

    return (
        _trading_account_to_dict(
            account
        )
    )


@app.post(
    "/api/accounts/discover"
)
def discover_broker_accounts(
    request: DiscoverBrokerAccountsRequest,
):
    if not (
        broker_registry
        .is_supported(
            request.broker
        )
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Broker is not supported yet: "
                f"{request.broker.value}"
            ),
        )

    try:
        adapter = (
            broker_registry
            .get(
                request.broker
            )
        )

    except KeyError as error:
        raise HTTPException(
            status_code=400,
            detail=(
                "Broker adapter is not available: "
                f"{request.broker.value}"
            ),
        ) from error

    credentials = (
        TradingAccountCredentials(
            values=(
                request
                .credentials
            ),
        )
    )

    try:
        accounts = (
            adapter.get_accounts(
                credentials=(
                    credentials
                ),

                mode=(
                    request.mode
                ),
            )
        )

    except Exception as error:
        return {
            "success": False,

            "broker":
                request
                .broker
                .value,

            "accounts": [],

            "error": repr(
                error
            ),
        }

    discovered = []

    for item in accounts:
        portfolio = None

        try:
            portfolio = (
                adapter.get_portfolio(
                    credentials=(
                        credentials
                    ),

                    broker_account_id=(
                        item
                        .broker_account_id
                    ),

                    mode=(
                        request.mode
                    ),
                )
            )

        except Exception:
            portfolio = None

        discovered.append(
            {
                "broker_account_id":
                    item
                    .broker_account_id,

                "name":
                    item.name,

                "status":
                    item.status,

                "account_type":
                    item
                    .account_type,

                "portfolio": (
                    _broker_portfolio_to_dict(
                        portfolio
                    )
                    if (
                        portfolio
                        is not None
                    )
                    else None
                ),
            }
        )

    api_usage_repository.record(
        source="web",
        operation=(
            "broker_accounts_discovered"
        ),
        weight=1,
    )

    return {
        "success": True,

        "broker":
            request
            .broker
            .value,

        "accounts":
            discovered,

        "error": None,
    }


@app.put(
    "/api/accounts/{account_id}"
)
def update_trading_account(
    account_id: str,

    request: UpdateTradingAccountRequest,
):
    if (
        request.broker
        is not None
        and not (
            broker_registry
            .is_supported(
                request.broker
            )
        )
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Broker is not supported yet: "
                f"{request.broker.value}"
            ),
        )

    try:
        account = (
            trading_account_service
            .update(
                account_id=(
                    account_id
                ),

                name=request.name,

                broker=request.broker,

                broker_account_id=(
                    request
                    .broker_account_id
                ),

                credentials=(
                    request.credentials
                ),

                mode=request.mode,

                commission_mode=(
                    request
                    .commission_mode
                ),

                custom_buy_commission_percent=(
                    request
                    .custom_buy_commission_percent
                ),

                custom_sell_commission_percent=(
                    request
                    .custom_sell_commission_percent
                ),

                enabled=request.enabled,
            )
        )

    except KeyError as error:
        raise HTTPException(
            status_code=404,
            detail="Trading account not found",
        ) from error

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(
                error
            ),
        ) from error

    operation_log_service.record(
        event_type=(
            "ACCOUNT_UPDATED"
        ),

        trading_account_id=(
            account.id
        ),

        details=(
            "name="
            f"{account.name} "

            "broker="
            f"{account.broker.value} "

            "mode="
            f"{account.mode.value}"
        ),
    )

    return (
        _trading_account_to_dict(
            account
        )
    )


@app.delete(
    "/api/accounts/{account_id}"
)
def delete_trading_account(
    account_id: str,
):
    try:
        trading_account_service\
            .delete(
                account_id
            )

    except KeyError as error:
        raise HTTPException(
            status_code=404,
            detail="Trading account not found",
        ) from error

    operation_log_service.record(
        event_type=(
            "ACCOUNT_REMOVED"
        ),

        trading_account_id=(
            account_id
        ),

        details=(
            "счёт удалён"
        ),
    )

    return {
        "status":
            "deleted",

        "account_id":
            account_id,
    }


@app.post(
    "/api/accounts/{account_id}/test"
)
def test_trading_account(
    account_id: str,
):
    try:
        account = (
            trading_account_service
            .get(
                account_id
            )
        )

        credentials = (
            trading_account_service
            .get_credentials(
                account_id
            )
        )

    except KeyError as error:
        raise HTTPException(
            status_code=404,
            detail="Trading account not found",
        ) from error

    try:
        adapter = (
            broker_registry
            .get(
                account.broker
            )
        )

    except KeyError as error:
        raise HTTPException(
            status_code=400,
            detail=(
                "Broker adapter is not available: "
                f"{account.broker.value}"
            ),
        ) from error

    result = (
        adapter.test_connection(
            credentials=(
                credentials
            ),

            broker_account_id=(
                account
                .broker_account_id
            ),

            mode=(
                account.mode
            ),
        )
    )

    return {
        "success":
            result.success,

        "broker":
            result
            .broker
            .value,

        "broker_account_id":
            result
            .broker_account_id,

        "account_found":
            result
            .account_found,

        "error":
            result.error,

        "accounts": [
            {
                "broker_account_id":
                    item
                    .broker_account_id,

                "name":
                    item.name,

                "status":
                    item.status,

                "account_type":
                    item
                    .account_type,
            }
            for item
            in (
                result.accounts
                or []
            )
        ],

        "portfolio": (
            _broker_portfolio_to_dict(
                result.portfolio
            )
            if (
                result.portfolio
                is not None
            )
            else None
        ),
    }


@app.get(
    "/api/accounts/{account_id}/portfolio"
)
def get_trading_account_portfolio(
    account_id: str,
):
    try:
        account = (
            trading_account_service
            .get(
                account_id
            )
        )

        credentials = (
            trading_account_service
            .get_credentials(
                account_id
            )
        )

    except KeyError as error:
        raise HTTPException(
            status_code=404,
            detail="Trading account not found",
        ) from error

    adapter = (
        broker_registry
        .get(
            account.broker
        )
    )

    try:
        portfolio = (
            adapter.get_portfolio(
                credentials=(
                    credentials
                ),

                broker_account_id=(
                    account
                    .broker_account_id
                ),

                mode=(
                    account.mode
                ),
            )
        )

    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=(
                "Broker portfolio request failed: "
                f"{error!r}"
            ),
        ) from error

    return (
        _broker_portfolio_to_dict(
            portfolio
        )
    )


# ============================================================
# MONEY MOVEMENTS 1.2 (пп. 4-5 плана)
# ============================================================

def _money_movement_to_dict(
    movement,
) -> dict:
    return {
        "id":
            movement.id,

        "created_at":
            movement
            .created_at,

        "trading_account_id":
            movement
            .trading_account_id,

        "amount":
            str(
                movement.amount
            ),

        "note":
            movement.note,
    }


def _performance_to_dict(
    report,
) -> dict:
    return {
        "trading_account_id":
            report
            .trading_account_id,

        "deposits_total":
            str(
                report
                .deposits_total
            ),

        "withdrawals_total":
            str(
                report
                .withdrawals_total
            ),

        "net_deposits":
            str(
                report
                .net_deposits
            ),

        "realized_profit":
            str(
                report
                .realized_profit
            ),

        "unrealized_profit":
            str(
                report
                .unrealized_profit
            ),

        "unrealized_estimated":
            report
            .unrealized_estimated,

        "open_invested":
            str(
                report
                .open_invested
            ),

        "historical_balance":
            str(
                report
                .historical_balance
            ),

        "roe_percent": (
            str(
                report
                .roe_percent
            )

            if (
                report
                .roe_percent
                is not None
            )

            else None
        ),

        "roi_percent": (
            str(
                report
                .roi_percent
            )

            if (
                report
                .roi_percent
                is not None
            )

            else None
        ),

        "movements_count":
            report
            .movements_count,
    }


def _build_account_performance(
    account,
):
    return (
        account_performance_service
        .build_report(
            trading_account_id=(
                account.id
            ),

            broker_account_id=(
                account
                .broker_account_id
            ),
        )
    )


@app.get(
    "/api/accounts"
    "/{account_id}/movements"
)
def get_money_movements(
    account_id: str,
):
    try:
        account = (
            trading_account_service
            .get(
                account_id
            )
        )

    except KeyError as error:
        raise HTTPException(
            status_code=404,
            detail=(
                "Trading account "
                "not found"
            ),
        ) from error

    movements = (
        money_movement_repository
        .get_by_account(
            account_id
        )
    )

    return {
        "movements": [
            _money_movement_to_dict(
                movement
            )

            for movement
            in movements
        ],

        "performance": (
            _performance_to_dict(
                _build_account_performance(
                    account
                )
            )
        ),
    }


@app.post(
    "/api/accounts"
    "/{account_id}/movements"
)
def add_money_movement(
    account_id: str,

    request: (
        AddMoneyMovementRequest
    ),
):
    try:
        account = (
            trading_account_service
            .get(
                account_id
            )
        )

    except KeyError as error:
        raise HTTPException(
            status_code=404,
            detail=(
                "Trading account "
                "not found"
            ),
        ) from error

    if (
        request.amount
        == 0
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Amount must be "
                "non-zero"
            ),
        )

    movement = (
        MoneyMovement(
            created_at=(
                datetime
                .now(
                    timezone.utc,
                )
                .isoformat()
            ),

            trading_account_id=(
                account_id
            ),

            amount=(
                request.amount
            ),

            note=(
                request
                .note
                .strip()
            ),
        )
    )

    money_movement_repository\
        .record(
            movement
        )

    is_deposit = (
        request.amount
        > 0
    )

    operation_log_service\
        .record(
            event_type=(
                "DEPOSIT"
                if is_deposit
                else "WITHDRAWAL"
            ),

            trading_account_id=(
                account_id
            ),

            ticker=(
                account.name
            ),

            details=(
                "сумма="
                f"{request.amount} "

                + (
                    request
                    .note
                    .strip()
                )
            ),
        )

    movements = (
        money_movement_repository
        .get_by_account(
            account_id
        )
    )

    return {
        "movements": [
            _money_movement_to_dict(
                movement
            )

            for movement
            in movements
        ],

        "performance": (
            _performance_to_dict(
                _build_account_performance(
                    account
                )
            )
        ),
    }


# ============================================================
# LIVE VALIDATION
# ============================================================

@app.post(
    "/api/start-live/validate"
)
def validate_live_start(
    request: StartSandboxRequest,
):
    if (
        request
        .trading_account_id
        is None
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "trading_account_id "
                "is required"
            ),
        )

    if not request.instruments:
        raise HTTPException(
            status_code=400,
            detail=(
                "No instruments selected"
            ),
        )

    config = (
        _build_multi_instrument_config(
            instruments=(
                request.instruments
            ),
        )
    )

    try:
        result = (
            live_start_validation_service
            .validate(
                trading_account_id=(
                    request
                    .trading_account_id
                ),

                config=config,
            )
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(
                error
            ),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "Live validation failed: "
                f"{error!r}"
            ),
        ) from error

    api_usage_repository.record(
        source="web",
        operation=(
            "live_start_validation"
        ),
        weight=1,
    )

    return {
        "success":
            result.success,

        "trading_account_id":
            result
            .trading_account_id,

        "broker":
            result.broker,

        "broker_account_id":
            result
            .broker_account_id,

        "account_name":
            result
            .account_name,

        "available_cash":
            str(
                result
                .available_cash
            ),

        "total_required_deposit":
            str(
                result
                .total_required_deposit
            ),

        "remaining_cash":
            str(
                result
                .remaining_cash
            ),

        "missing_cash":
            str(
                result
                .missing_cash
            ),

        "can_start":
            result
            .can_start,

        "can_start_forced":
            result
            .can_start_forced,

        "capital_utilization_percent":
            str(
                result
                .capital_utilization_percent
            ),

        "buy_commission_percent":
            str(
                result
                .buy_commission_percent
            ),

        "sell_commission_percent":
            str(
                result
                .sell_commission_percent
            ),

        "instruments": [
            {
                "ticker":
                    instrument
                    .ticker,

                "instrument_uid":
                    instrument
                    .instrument_uid,

                "current_price":
                    str(
                        instrument
                        .current_price
                    ),

                "min_grid_price":
                    str(
                        instrument
                        .min_grid_price
                    ),

                "grid_step":
                    str(
                        instrument
                        .grid_step
                    ),

                "levels_count":
                    instrument
                    .levels_count,

                "quantity":
                    instrument
                    .quantity,
            }
            for instrument
            in result.instruments
        ],
    }


# ============================================================
# LIVE START
# ============================================================

@app.post(
    "/api/start-live"
)
def start_live(
    request: StartSandboxRequest,
):
    api_usage_repository.record(
        source="web",
        operation="start_live",
        weight=1,
    )

    guard = (
        TradingModeGuard(
            settings=settings,
        )
    )

    try:
        guard.ensure_live_order_allowed()

    except RuntimeError as error:
        raise HTTPException(
            status_code=403,
            detail=str(
                error
            ),
        ) from error

    if not request.instruments:
        raise HTTPException(
            status_code=400,
            detail=(
                "No instruments selected"
            ),
        )

    config = (
        _build_multi_instrument_config(
            instruments=(
                request.instruments
            ),
        )
    )

    factory = (
        MultiInstrumentTradingSessionFactory(
            settings=settings,
            knowledge_engine=(
                knowledge_engine
            ),

            operation_log=(
                operation_log_service
            ),

            notifier=(
                telegram_notifier
            ),
        )
    )

    runner = None
    validation_result = None

    try:
        if (
            request
            .trading_account_id
            is not None
        ):
            try:
                esm_account = (
                    trading_account_service
                    .get(
                        request
                        .trading_account_id
                    )
                )

            except KeyError as error:
                raise HTTPException(
                    status_code=404,
                    detail=(
                        "Trading account "
                        "not found"
                    ),
                ) from error

            if not esm_account.enabled:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Trading account "
                        "is disabled"
                    ),
                )

            if (
                esm_account.broker
                != BrokerType.TINVEST
            ):
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Live trading for "
                        f"{esm_account.broker.value} "
                        "is not supported yet"
                    ),
                )

            if (
                esm_account.mode
                != TradingAccountMode.LIVE
            ):
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Selected account "
                        "is not LIVE"
                    ),
                )

            credentials = (
                trading_account_service
                .get_credentials(
                    esm_account.id
                )
            )

            # Re-validate server-side at the moment of start.
            # This is the single authoritative planned capital stored
            # for the session; the frontend does not calculate it again.
            validation_result = (
                live_start_validation_service
                .validate(
                    trading_account_id=(
                        esm_account.id
                    ),
                    config=config,
                )
            )

            context = (
                factory
                .create_live_session_for_account(
                    config=config,

                    token=(
                        credentials
                        .require(
                            "token"
                        )
                    ),

                    broker_account_id=(
                        esm_account
                        .broker_account_id
                    ),

                    buy_commission_percent=(
                        esm_account
                        .get_expected_buy_commission_percent()
                    ),

                    sell_commission_percent=(
                        esm_account
                        .get_expected_sell_commission_percent()
                    ),
                )
            )

            trading_account_id = (
                esm_account.id
            )

            broker_name = (
                esm_account
                .broker
                .value
            )

        else:
            context = (
                factory
                .create_live_session(
                    config=config,
                )
            )

            trading_account_id = (
                _build_trading_account_id(
                    mode="live",

                    broker_account_id=(
                        context.account_id
                    ),
                )
            )

            broker_name = (
                "tinvest"
            )

        runner_session_id = (
            _build_runner_session_id(
                mode="live",

                broker_account_id=(
                    context.account_id
                ),

                instruments=(
                    request.instruments
                ),
            )
        )

        if (
            request
            .trading_account_id
            is not None
        ):
            runner_session_id = (
                f"{broker_name}:"
                f"{trading_account_id}:"
                f"{runner_session_id}"
            )

        runner_session_id = (
            _uniquify_runner_session_id(
                runner_session_id
            )
        )

        runner = (
            WebRunnerService(
                context=context,

                api_usage_repository=(
                    api_usage_repository
                ),

                reconciliation_journal=(
                    reconciliation_journal
                ),

                polling_interval_seconds=10,

                state_service=(
                    trading_state_service
                ),

                session_id=(
                    runner_session_id
                ),

                trading_account_id=(
                    trading_account_id
                ),
                planned_initial_capital=(
                    validation_result.total_required_deposit
                    if validation_result is not None
                    else None
                ),
                lifecycle_status="RUNNING",

                auto_rebalance=(
                    _build_auto_rebalance_service(
                        request=(
                            request
                        ),

                        trading_account_id=(
                            trading_account_id
                        ),
                    )
                ),

                operation_log=(
                    operation_log_service
                ),
            )
        )

        web_runner_registry.start(
            runner=runner,
        )

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "Live trading session failed: "
                f"{error!r}"
            ),
        ) from error

    started_sessions = []

    try:
        for instrument in (
            request.instruments
        ):
            session = (
                session_registry
                .start_session(
                    ticker=(
                        instrument.ticker
                    ),

                    levels=(
                        instrument.levels
                    ),

                    quantity=(
                        instrument.quantity
                    ),
                )
            )

            started_sessions.append(
                session
            )

    except Exception:
        if (
            runner
            is not None
        ):
            runner.stop()

        raise

    return {
        "status":
            "started",

        "mode":
            "live",

        "execution_status":
            "started",

        "force":
            request.force,

        "account_id":
            context.account_id,

        "trading_account_id":
            trading_account_id,

        "broker":
            broker_name,

        "legacy_account": (
            request
            .trading_account_id
            is None
        ),

        "runner_session_id":
            runner.session_id,

        "sessions": [
            _build_display_session(
                web_session=session,
            )
            for session
            in started_sessions
        ],
    }


# ============================================================
# HEALTH
# ============================================================

@app.get(
    "/api/health"
)
def health():
    return {
        "status":
            "ok",

        "version":
            APP_VERSION,

        "trading_mode":
            settings
            .trading_mode,

        "live_trading_enabled":
            settings
            .live_trading_enabled,

        "real_sandbox_enabled":
            _is_real_sandbox_enabled(),

        "state_persistence_enabled":
            True,

        "multi_account_enabled":
            True,

        "multi_broker_architecture":
            True,

        "database_path":
            str(
                database_path
            ),
    }


@app.get(
    "/api/version"
)
def version():
    return {
        "version":
            APP_VERSION,
    }


# ============================================================
# ACTIVE STATE HELPERS
# ============================================================

def _build_active_state_key(
    state,
) -> tuple:
    instrument_keys = []

    for instrument in state.instruments:
        config = getattr(
            instrument,
            "grid_config",
            None,
        )

        quantity = (
            getattr(
                config,
                "quantity",
                None,
            )
            if config is not None
            else None
        )

        if quantity is None:
            quantity = (
                instrument.open_positions[0].quantity
                if instrument.open_positions
                else 1
            )

        instrument_keys.append(
            (
                instrument.ticker.upper(),
                len(instrument.levels),
                int(quantity),
            )
        )

    instrument_keys.sort()

    return (
        state.trading_account_id,
        state.broker_account_id,
        state.mode.lower(),
        tuple(instrument_keys),
    )


def _deduplicate_active_states(
    states,
):
    seen = set()
    result = []

    for state in states:
        key = _build_active_state_key(
            state
        )

        if key in seen:
            continue

        seen.add(key)
        result.append(state)

    return result


# ============================================================
# DASHBOARD
# ============================================================

@app.get(
    "/api/dashboard"
)
def dashboard():
    sessions = [
        _build_display_session(
            web_session=session,
        )
        for session
        in session_registry
        .get_sessions()
    ]

    active_states = (
        _deduplicate_active_states(
            [
                state
                for state
                in trading_state_repository
                .get_active()
                if state.mode.lower() == "live"
            ]
        )
    )

    configured_accounts = (
        trading_account_service
        .get_all()
    )

    # Fixed amount required when each active strategy was started.
    initial_capital = sum(
        (
            getattr(
                state,
                "initial_deposit",
                None,
            )
            or Decimal("0")
        )
        for state
        in active_states
    )

    # Current actual money in open positions. We calculate it from
    # recovered/live GridEngine objects so BUY commission is included.
    invested_cash = Decimal("0")
    reserved_cash = Decimal("0")

    for runner in (
        web_runner_registry
        .get_all()
    ):
        if (
            getattr(
                runner.context,
                "mode",
                "sandbox",
            ).lower()
            != "live"
        ):
            continue

        for trading_session in (
            runner.context
            .session
            .sessions
            .values()
        ):
            engine = (
                trading_session
                .grid_engine
            )

            for position in (
                engine
                .open_positions
                .values()
            ):
                invested_cash += (
                    Decimal(
                        str(position.entry_price)
                    )
                    * Decimal(
                        str(position.quantity)
                    )
                    + Decimal(
                        str(
                            getattr(
                                position,
                                "buy_commission",
                                Decimal("0"),
                            )
                            or Decimal("0")
                        )
                    )
                )

        reservation_manager = (
            runner.context
            .trade_capital_service
            .reservation_manager
        )

        reserved_cash += (
            reservation_manager
            .get_reserved_total()
        )

    # Fallback if the application is between DB recovery and runner setup.
    if not web_runner_registry.get_all():
        reserved_cash = sum(
            (
                state.reserved_cash
                or Decimal("0")
            )
            for state
            in active_states
        )

        for state in active_states:
            for instrument in state.instruments:
                for position in instrument.open_positions:
                    purchase_cost = getattr(
                        position,
                        "purchase_cost",
                        None,
                    )

                    if purchase_cost is not None:
                        invested_cash += Decimal(
                            str(purchase_cost)
                        )

    # Real free broker cash: each enabled LIVE account exactly once.
    live_cash = Decimal("0")
    live_cash_accounts = 0

    for account in configured_accounts:
        if (
            not account.enabled
            or account.mode
            != TradingAccountMode.LIVE
        ):
            continue

        try:
            adapter = (
                broker_registry
                .get(account.broker)
            )

            credentials = (
                trading_account_service
                .get_credentials(
                    account.id
                )
            )

            portfolio = (
                adapter.get_portfolio(
                    credentials=credentials,
                    broker_account_id=(
                        account.broker_account_id
                    ),
                    mode=account.mode,
                )
            )

            live_cash += portfolio.cash
            live_cash_accounts += 1

        except Exception as error:
            print(
                "DASHBOARD PORTFOLIO ERROR:",
                account.id,
                repr(error),
            )

    if live_cash_accounts == 0:
        latest_cash_by_broker: dict[
            str,
            Decimal,
        ] = {}

        for state in active_states:
            latest_cash_by_broker[
                state.broker_account_id
            ] = state.available_cash

        live_cash = sum(
            latest_cash_by_broker.values(),
            Decimal("0"),
        )

    realized_profit = sum(
        Decimal(
            str(
                session.get(
                    "realized_profit",
                    0,
                )
            )
        )
        for session
        in sessions
    )

    unrealized_profit = sum(
        Decimal(
            str(
                session.get(
                    "unrealized_profit",
                    0,
                )
            )
        )
        for session
        in sessions
    )

    total_profit = (
        realized_profit
        + unrealized_profit
    )

    return {
        "accounts":
            len(configured_accounts),

        "active_accounts":
            len(
                {
                    state.trading_account_id
                    for state
                    in active_states
                }
            ),

        "capital": (
            float(initial_capital)
            if initial_capital > 0
            else None
        ),

        "invested_cash":
            float(invested_cash),

        "available_cash": (
            float(live_cash)
            if (
                live_cash_accounts > 0
                or active_states
            )
            else None
        ),

        "reserved_cash": (
            float(reserved_cash)
            if active_states
            else None
        ),

        "active_positions":
            sum(
                session["positions"]
                for session
                in sessions
            ),

        "realized_profit":
            float(realized_profit),

        "unrealized_profit":
            float(unrealized_profit),

        "profit":
            float(total_profit),

        "instruments": [
            session["ticker"]
            for session
            in sessions
        ],
    }


# ============================================================
# API USAGE
# ============================================================

@app.get(
    "/api/api-usage"
)
def api_usage():
    summary = (
        api_usage_repository
        .summarize(
            active_sessions_count=(
                web_runner_registry
                .get_active_count()
            ),
        )
    )

    return {
        "total_weight":
            summary.total_weight,

        "events_count":
            summary.events_count,

        "by_operation":
            summary.by_operation,

        "last_1s_weight":
            summary.last_1s_weight,

        "last_60s_weight":
            summary.last_60s_weight,

        "last_300s_weight":
            summary.last_300s_weight,

        "active_sessions_count":
            summary
            .active_sessions_count,

        "per_minute_per_session":
            summary
            .per_minute_per_session,

        "forecast_5_sessions_per_minute":
            summary
            .forecast_5_sessions_per_minute,

        "forecast_10_sessions_per_minute":
            summary
            .forecast_10_sessions_per_minute,

        "forecast_20_sessions_per_minute":
            summary
            .forecast_20_sessions_per_minute,
    }


# ============================================================
# RECONCILIATION EVENTS 1.1
# ============================================================

@app.get(
    "/api/reconciliation/events"
)
def reconciliation_events(
    limit: int = 100,
):
    safe_limit = (
        max(
            1,

            min(
                limit,
                500,
            ),
        )
    )

    events = (
        reconciliation_event_repository
        .recent(
            limit=safe_limit,
        )
    )

    return {
        "events": [
            {
                "created_at":
                    event
                    .created_at,

                "trading_account_id":
                    event
                    .trading_account_id,

                "instrument_id":
                    event
                    .instrument_id,

                "event_type":
                    event
                    .event_type,

                "details":
                    event
                    .details,
            }

            for event
            in events
        ],

        "counts_by_type":
            (
                reconciliation_event_repository
                .count_by_type()
            ),
    }


# ============================================================
# AUTH 1.2 (п. 6)
# ============================================================

def _auth_user(
    request: Request,
):
    token = (
        _token_from_request(
            request
        )
    )

    if not token:
        raise HTTPException(
            status_code=401,
            detail=(
                "Требуется "
                "авторизация"
            ),
        )

    user = (
        auth_service
        .get_user_by_token(
            token
        )
    )

    if (
        user
        is None
        or not token
    ):
        raise HTTPException(
            status_code=401,
            detail=(
                "Сессия истекла, "
                "войдите заново"
            ),
        )

    return (
        user,

        token,
    )


def _set_auth_cookie(
    response: Response,
    token: str,
) -> None:
    response.set_cookie(
        key=(
            AUTH_COOKIE
        ),

        value=(
            token
        ),

        max_age=(
            30
            * 24
            * 60
            * 60
        ),

        samesite=(
            "lax"
        ),
    )


@app.get(
    "/api/auth/status"
)
def auth_status(
    device_id: str = "web",
):
    return {
        "auth_required": (
            _auth_is_enforced()
        ),

        "has_users": (
            auth_service
            .has_users()
        ),

        "device_has_pin": (
            auth_service
            .device_has_pin(
                device_id
            )
        ),

        "device_has_biometric": (
            auth_service
            .device_has_biometric(
                device_id
            )
        ),
    }


@app.post(
    "/api/auth/register"
)
def auth_register(
    request: (
        RegisterRequest
    ),

    response: Response,
):
    if (
        auth_service
        .has_users()
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Пользователь уже "
                "зарегистрирован. "
                "Войдите по логину "
                "и паролю."
            ),
        )

    try:
        user, token = (
            auth_service
            .register(
                full_name=(
                    request
                    .full_name
                ),

                phone=(
                    request
                    .phone
                ),

                email=(
                    request
                    .email
                ),

                birth_date=(
                    request
                    .birth_date
                ),

                login=(
                    request
                    .login
                ),

                password=(
                    request
                    .password
                ),

                device_id=(
                    request
                    .device_id
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

    _set_auth_cookie(
        response,

        token,
    )

    _register_user_on_head(
        user.id
    )

    operation_log_service\
        .record(
            event_type=(
                "USER_REGISTERED"
            ),

            ticker=(
                user.login
            ),

            details=(
                user
                .full_name
            ),
        )

    return {
        "user": {
            "id": (
                user.id
            ),

            "login": (
                user.login
            ),

            "full_name": (
                user
                .full_name
            ),
        }
    }


@app.post(
    "/api/auth/login"
)
def auth_login(
    request: (
        LoginRequest
    ),

    response: Response,
):
    try:
        user, token = (
            auth_service
            .login(
                login=(
                    request
                    .login
                ),

                password=(
                    request
                    .password
                ),

                device_id=(
                    request
                    .device_id
                ),
            )
        )

    except ValueError as error:
        raise HTTPException(
            status_code=401,
            detail=str(
                error
            ),
        ) from error

    _set_auth_cookie(
        response,

        token,
    )

    _login_user_on_head(
        user.id
    )

    return {
        "user": {
            "id": (
                user.id
            ),

            "login": (
                user.login
            ),

            "full_name": (
                user
                .full_name
            ),
        }
    }


@app.post(
    "/api/auth/pin/verify"
)
def auth_pin_verify(
    request: (
        PinVerifyRequest
    ),

    response: Response,
):
    try:
        user, token = (
            auth_service
            .verify_pin(
                device_id=(
                    request
                    .device_id
                ),

                pin=(
                    request
                    .pin
                ),
            )
        )

    except ValueError as error:
        raise HTTPException(
            status_code=401,
            detail=str(
                error
            ),
        ) from error

    _set_auth_cookie(
        response,

        token,
    )

    return {
        "user": {
            "id": (
                user.id
            ),

            "login": (
                user.login
            ),

            "full_name": (
                user
                .full_name
            ),
        }
    }


@app.post(
    "/api/auth/biometric/verify"
)
def auth_biometric_verify(
    request: (
        BiometricVerifyRequest
    ),

    response: Response,
):
    try:
        user, token = (
            auth_service
            .verify_biometric(
                device_id=(
                    request
                    .device_id
                ),

                credential_id=(
                    request
                    .credential_id
                ),
            )
        )

    except ValueError as error:
        raise HTTPException(
            status_code=401,
            detail=str(
                error
            ),
        ) from error

    _set_auth_cookie(
        response,

        token,
    )

    return {
        "user": {
            "id": (
                user.id
            ),

            "login": (
                user.login
            ),

            "full_name": (
                user
                .full_name
            ),
        }
    }


@app.get(
    "/api/auth/me"
)
def auth_me(
    request: Request,
):
    user, _ = (
        _auth_user(
            request
        )
    )

    return {
        "user": {
            "id": (
                user.id
            ),

            "login": (
                user.login
            ),

            "full_name": (
                user
                .full_name
            ),
        }
    }


@app.post(
    "/api/auth/logout"
)
def auth_logout(
    request: Request,

    response: Response,
):
    _, token = (
        _auth_user(
            request
        )
    )

    auth_service.logout(
        token
    )

    response.delete_cookie(
        key=(
            AUTH_COOKIE
        ),
    )

    return {
        "status": "ok"
    }


@app.post(
    "/api/auth/pin/set"
)
def auth_pin_set(
    request: (
        PinSetRequest
    ),

    raw_request: Request,
):
    _, token = (
        _auth_user(
            raw_request
        )
    )

    try:
        auth_service.set_pin(
            token=(
                token
            ),

            device_id=(
                request
                .device_id
            ),

            pin=(
                request
                .pin
            ),
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(
                error
            ),
        ) from error

    return {
        "status": "ok"
    }


@app.post(
    "/api/auth/biometric/register"
)
def auth_biometric_register(
    request: (
        BiometricRegisterRequest
    ),

    raw_request: Request,
):
    _, token = (
        _auth_user(
            raw_request
        )
    )

    auth_service.set_biometric(
        token=(
            token
        ),

        device_id=(
            request
            .device_id
            ),

        credential_id=(
            request
            .credential_id
        ),
    )

    return {
        "status": "ok"
    }


@app.post(
    "/api/auth/biometric/disable"
)
def auth_biometric_disable(
    request: (
        BiometricRegisterRequest
    ),

    raw_request: Request,
):
    _, token = (
        _auth_user(
            raw_request
        )
    )

    auth_service.disable_biometric(
        token=(
            token
        ),

        device_id=(
            request
            .device_id
        ),
    )

    return {
        "status": "ok"
    }


# ============================================================
# OPERATIONS LOG 1.2
# ============================================================

@app.get(
    "/api/operations"
)
def operations(
    limit: int = 100,
):
    safe_limit = (
        max(
            1,

            min(
                limit,
                500,
            ),
        )
    )

    events = [
        event

        for event
        in (
            operation_log_repository
            .recent(
                limit=safe_limit,
            )
        )

        #
        # TRAILING — служебные точки
        # истории траллов: только для
        # графика, не для ленты истории.
        #
        if (
            event
            .event_type
            != "TRAILING"
        )
    ]

    return {
        "operations": [
            {
                "created_at":
                    event
                    .created_at,

                "trading_account_id":
                    event
                    .trading_account_id,

                "instrument_id":
                    event
                    .instrument_id,

                "ticker":
                    event
                    .ticker,

                "event_type":
                    event
                    .event_type,

                "details":
                    event
                    .details,
            }

            for event
            in events
        ],
    }


# ============================================================
# PHANTOM AUDIT 1.2 (7.4)
# ============================================================

def _collect_broker_positions_for_snapshots(
    snapshots,
) -> tuple[
    dict[
        str,
        dict[
            str,
            int,
        ],
    ],

    list[str],
]:
    """
    Для каждого уникального
    (счёт, брокерский аккаунт)
    из snapshot-ов запрашивает
    реальные позиции брокера.

    Возвращает карту
    broker_account_id ->
    instrument_uid -> лоты
    и список ошибок проверки.
    """

    result: dict[
        str,
        dict[
            str,
            int,
        ],
    ] = {}

    errors: list[
        str
    ] = []

    checked: set[
        tuple[
            str,
            str,
            str,
        ]
    ] = set()

    for snapshot in snapshots:
        key = (
            snapshot
            .trading_account_id,

            snapshot
            .broker_account_id,

            snapshot
            .mode
            .lower(),
        )

        if (
            key
            in checked
        ):
            continue

        checked.add(
            key
        )

        try:
            account = (
                trading_account_service
                .get(
                    snapshot
                    .trading_account_id
                )
            )

        except KeyError:
            errors.append(
                "Счёт не найден в базе: "
                f"{snapshot.trading_account_id}"
                " (проверка невозможна)"
            )

            continue

        if (
            not account.enabled
        ):
            errors.append(
                "Счёт отключён: "
                f"{account.name}"
            )

            continue

        try:
            token = (
                trading_account_service
                .get_credentials(
                    account.id
                )
                .require(
                    "token"
                )
            )

        except ValueError:
            errors.append(
                "Нет токена у счёта: "
                f"{account.name}"
            )

            continue

        try:
            provider = (
                TInvestLivePositionProvider(
                    client_factory=(
                        TInvestClientFactory(
                            token=(
                                token
                            ),
                        )
                    ),

                    use_sandbox=(
                        snapshot
                        .mode
                        .lower()
                        == "sandbox"
                    ),
                )
            )

            positions = (
                provider
                .get_positions(
                    account_id=(
                        snapshot
                        .broker_account_id
                    ),
                )
            )

        except Exception as error:
            errors.append(
                "Ошибка сверки счёта "
                f"{snapshot.broker_account_id}: "
                f"{error!r}"
            )

            continue

        result[
            snapshot
            .broker_account_id
        ] = {
            position
            .instrument_uid: (
                position
                .quantity_lots
            )

            for position
            in positions
        }

    return (
        result,
        errors,
    )


def _active_runner_session_ids() -> (
    set[str]
):
    return {
        session_id

        for session_id
        in (
            web_runner_registry
            .runners_by_session_id
        )
    }


@app.get(
    "/api/phantoms"
)
def get_phantoms():
    snapshots = (
        trading_state_repository
        .get_all()
    )

    (
        broker_positions,
        errors,
    ) = (
        _collect_broker_positions_for_snapshots(
            snapshots
        )
    )

    report = (
        phantom_position_auditor
        .audit(
            snapshots=(
                snapshots
            ),

            broker_positions_by_account=(
                broker_positions
            ),

            active_session_ids=(
                _active_runner_session_ids()
            ),
        )
    )

    return {
        "phantoms": [
            {
                "session_id":
                    phantom
                    .session_id,

                "trading_account_id":
                    phantom
                    .trading_account_id,

                "broker_account_id":
                    phantom
                    .broker_account_id,

                "mode":
                    phantom
                    .mode,

                "status":
                    phantom
                    .status,

                "ticker":
                    phantom
                    .ticker,

                "instrument_uid":
                    phantom
                    .instrument_uid,

                "open_positions":
                    phantom
                    .open_positions,

                "open_lots":
                    phantom
                    .open_lots,

                "active_orders":
                    phantom
                    .active_orders,

                "broker_lots":
                    phantom
                    .broker_lots,
            }

            for phantom
            in (
                report
                .phantoms
            )
        ],

        "errors": (
            errors
            + report
            .errors
        ),

        "checked_accounts": (
            report
            .checked_accounts
        ),
    }


@app.post(
    "/api/phantoms/resolve"
)
def resolve_phantoms(
    request: PhantomResolveRequest,
):
    resolved = []

    for item in request.items:
        state = (
            trading_state_repository
            .get(
                item.session_id
            )
        )

        if (
            state is None
        ):
            continue

        uids = set(
            item
            .instrument_uids
        )

        cleaned = (
            phantom_position_auditor
            .clean(
                state=state,

                instrument_uids=(
                    uids
                ),
            )
        )

        tickers = [
            instrument
            .ticker

            for instrument
            in (
                state
                .instruments
            )

            if (
                instrument
                .instrument_uid
                in uids
            )
        ]

        snapshot_deleted = (
            cleaned
            is None
        )

        if (
            snapshot_deleted
        ):
            trading_state_repository\
                .delete(
                    item
                    .session_id
                )

        else:
            trading_state_repository\
                .save(
                    cleaned
                )

        operation_log_service\
            .record(
                event_type=(
                    "PHANTOMS_REMOVED"
                ),

                trading_account_id=(
                    state
                    .trading_account_id
                ),

                ticker=(
                    ", ".join(
                        tickers
                    )
                ),

                details=(
                    "инструменты="
                    f"{sorted(uids)} "

                    "snapshot="
                    f"{item.session_id} "

                    "удалён целиком="
                    f"{snapshot_deleted}"
                ),
            )

        resolved.append(
            {
                "session_id":
                    item
                    .session_id,

                "removed_instruments":
                    len(
                        uids
                    ),

                "snapshot_deleted":
                    snapshot_deleted,
            }
        )

    return {
        "resolved":
            resolved,
    }


# ============================================================
# KNOWLEDGE INSTRUMENTS 1.1
# ============================================================

@app.get(
    "/api/knowledge/instruments"
)
def knowledge_instruments():
    statistics_list = (
        knowledge_engine
        .get_all()
    )

    return {
        "instruments": [
            {
                "instrument_id":
                    statistics
                    .instrument_id,

                "total_cycles":
                    statistics
                    .total_cycles,

                "profitable_cycles":
                    statistics
                    .profitable_cycles,

                "losing_cycles":
                    statistics
                    .losing_cycles,

                "total_profit":
                    str(
                        statistics
                        .total_profit,
                    ),

                "max_drawdown":
                    str(
                        statistics
                        .max_drawdown,
                    ),

                "average_cycle_profit":
                    str(
                        statistics
                        .average_cycle_profit,
                    ),

                "compensation_closes":
                    statistics
                    .compensation_closes,

                "total_trades":
                    statistics
                    .total_trades,
            }

            for statistics
            in statistics_list
        ],
    }


@app.get(
    "/api/runner-status"
)
def runner_status():
    return {
        "runners": [
            {
                "session_id":
                    runner
                    .session_id,

                "trading_account_id":
                    runner
                    .trading_account_id,

                "is_running":
                    status
                    .is_running,

                "lifecycle_status":
                    getattr(
                        status,
                        "lifecycle_status",
                        (
                            "RUNNING"
                            if status.is_running
                            else "STOPPED"
                        ),
                    ),

                "last_tick_at":
                    status
                    .last_tick_at,

                "last_error":
                    status
                    .last_error,

                "ticks_count":
                    status
                    .ticks_count,

                "prices_checked_total":
                    status
                    .prices_checked_total,

                "orders_placed_total":
                    status
                    .orders_placed_total,

                "executions_total":
                    status
                    .executions_total,
            }
            for runner
            in web_runner_registry
            .get_all()

            for status
            in [
                runner.get_status()
            ]
        ],
    }


# ============================================================
# INSTRUMENTS
# ============================================================

@app.get(
    "/api/instruments"
)
def instruments():
    # Selected instruments are a user choice.
    # Do not inject SBER/GAZP/LKOH automatically.
    return {
        "instruments": [],
    }


@app.get(
    "/api/instruments/search"
)
def search_instruments(
    query: str = "",
    trading_account_id: str | None = None,
    limit: int = 50,
):
    try:
        items = (
            instrument_catalog_service
            .search(
                query=query,
                trading_account_id=(
                    trading_account_id
                ),
                limit=limit,
            )
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=(
                "T-Invest instrument search failed: "
                f"{error!r}"
            ),
        ) from error

    api_usage_repository.record(
        source="web",
        operation="instrument_search",
        weight=1,
    )

    return {
        "instruments": [
            {
                "instrument_uid":
                    item.instrument_uid,
                "ticker":
                    item.ticker,
                "name":
                    item.name,
                "currency":
                    item.currency,
                "lot_size":
                    item.lot_size,
                "min_price_step":
                    str(
                        item.min_price_step
                    ),
            }
            for item
            in items
        ],
    }


# ============================================================
# INSTRUMENT SELECTION 1.1 (индексный режим)
# ============================================================

class SelectionCandidateRequest(
    BaseModel,
):
    ticker: str

    instrument_uid: str = ""

    name: str = ""

    risk_value: (
        Decimal | None
    ) = None

    risk_band: (
        str | None
    ) = None

    volatility_percent: (
        Decimal | None
    ) = None

    max_drawdown_percent: (
        Decimal | None
    ) = None

    confidence_value: (
        Decimal | None
    ) = None


class InstrumentSelectionRequest(
    BaseModel,
):
    capital: Decimal

    max_instruments: int = 5

    min_confidence: (
        Decimal
    ) = Decimal("40")

    allow_high_risk: bool = False

    candidates: list[
        SelectionCandidateRequest
    ] = []


class IndexSelectionRequest(
    BaseModel,
):
    index_id: str

    capital: Decimal

    quantity: int = 1

    trading_account_id: (
        str | None
    ) = None


class AutoSelectionRequest(
    BaseModel,
):
    capital: Decimal

    quantity: int = 1

    max_price: (
        Decimal | None
    ) = None

    max_instruments: int = 5

    desired_levels: int = 30

    min_levels: int = 10

    trading_account_id: (
        str | None
    ) = None


@app.post(
    "/api/instrument-selection/preview"
)
def instrument_selection_preview(
    request: (
        InstrumentSelectionRequest
    ),
):
    from application.instrument_selector import (
        InstrumentCandidate,
        InstrumentSelector,
    )
    from strategy.confidence_score import (
        ConfidenceScore,
        ConfidenceScoreCalculator,
    )
    from strategy.risk_score import (
        HIGH_BAND,
        LOW_BAND,
        MEDIUM_BAND,
        RiskScore,
    )

    def _band_by_value(
        value: Decimal,
    ) -> str:
        if value < Decimal("30"):
            return LOW_BAND

        if value < Decimal("60"):
            return MEDIUM_BAND

        return HIGH_BAND

    candidates = []

    for item in (
        request
        .candidates
    ):
        if not item.ticker.strip():
            raise HTTPException(
                status_code=400,
                detail=(
                    "Candidate ticker "
                    "must not be empty"
                ),
            )

        risk_value = (
            item.risk_value

            if item.risk_value
            is not None

            else Decimal("0")
        )

        risk_score = (
            RiskScore(
                instrument_id=(
                    item
                    .instrument_uid
                    or item.ticker
                ),

                value=(
                    risk_value
                ),

                band=(
                    item.risk_band

                    if item.risk_band

                    else _band_by_value(
                        risk_value,
                    )
                ),

                volatility_percent=(
                    item
                    .volatility_percent

                    if item
                    .volatility_percent
                    is not None

                    else Decimal("0")
                ),

                max_drawdown_percent=(
                    item
                    .max_drawdown_percent

                    if item
                    .max_drawdown_percent
                    is not None

                    else Decimal("0")
                ),
            )
        )

        if (
            item
            .confidence_value
            is not None
        ):
            confidence_score = (
                ConfidenceScore(
                    instrument_id=(
                        item
                        .instrument_uid
                        or item.ticker
                    ),

                    value=(
                        item
                        .confidence_value
                    ),

                    band="",
                )
            )

        else:
            knowledge_statistics = (
                knowledge_engine
                .get(
                    instrument_id=(
                        item
                        .instrument_uid
                        or item
                        .ticker
                    ),
                )
            )

            confidence_score = (
                ConfidenceScoreCalculator()
                .calculate(
                    instrument_id=(
                        item
                        .instrument_uid
                        or item.ticker
                    ),

                    risk_score=(
                        risk_score
                    ),

                    statistics=(
                        knowledge_statistics
                    ),
                )
            )

        candidates.append(
            InstrumentCandidate(
                ticker=(
                    item.ticker
                    .strip()
                    .upper()
                ),

                instrument_uid=(
                    item
                    .instrument_uid
                    or item.ticker
                ),

                name=(
                    item.name
                ),

                risk_score=(
                    risk_score
                ),

                confidence_score=(
                    confidence_score
                ),
            )
        )

    try:
        plan = (
            InstrumentSelector(
                max_instruments=(
                    request
                    .max_instruments
                ),

                min_confidence=(
                    request
                    .min_confidence
                ),

                allow_high_risk=(
                    request
                    .allow_high_risk
                ),
            )
            .build_plan(
                candidates=candidates,

                capital=(
                    request
                    .capital
                ),
            )
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    return {
        "capital":
            str(
                plan.capital
            ),

        "selections": [
            {
                "ticker":
                    selection
                    .ticker,

                "instrument_uid":
                    selection
                    .instrument_uid,

                "name":
                    selection
                    .name,

                "weight_percent":
                    str(
                        selection
                        .weight_percent
                    ),

                "allocated_capital":
                    str(
                        selection
                        .allocated_capital
                    ),

                "confidence_value":
                    (
                        str(
                            selection
                            .confidence_value
                        )

                        if (
                            selection
                            .confidence_value
                        )

                        else None
                    ),

                "risk_band":
                    selection
                    .risk_band,
            }

            for selection
            in (
                plan
                .selections
            )
        ],

        "rejected": [
            {
                "ticker":
                    rejected
                    .ticker,

                "reason":
                    rejected
                    .reason,
            }

            for rejected
            in (
                plan.rejected
            )
        ],
    }


def _grid_selection_to_dict(
    selection,
) -> dict:
    return {
        "ticker":
            selection
            .ticker,

        "instrument_uid":
            selection
            .instrument_uid,

        "name":
            selection
            .name,

        "currency":
            selection
            .currency,

        "price":
            str(
                selection
                .price
            ),

        "lot_size":
            selection
            .lot_size,

        "quantity":
            selection
            .quantity,

        "levels":
            selection
            .levels,

        "volatility_percent":
            str(
                selection
                .volatility_percent
            ),

        "risk_band":
            selection
            .risk_band,

        "estimated_cost":
            str(
                selection
                .estimated_cost
            ),

        "allocated_capital":
            str(
                selection
                .allocated_capital
            ),
    }


def _grid_selection_plan_response(
    mode: str,
    index_id: (
        str | None
    ),
    plan,
) -> dict:
    return {
        "mode": mode,

        "index_id":
            index_id,

        "capital":
            str(
                plan.capital
            ),

        "selections": [
            _grid_selection_to_dict(
                selection,
            )

            for selection
            in (
                plan
                .selections
            )
        ],

        "rejected": [
            {
                "ticker":
                    rejected
                    .ticker,

                "reason":
                    rejected
                    .reason,
            }

            for rejected
            in (
                plan.rejected
            )
        ],

        "spent_capital":
            str(
                plan
                .spent_capital
            ),

        "remaining_capital":
            str(
                plan
                .remaining_capital
            ),
    }


def _snapshots_with_missing_rejected(
    snapshots,
    requested_tickers: (
        list[str]
    ),
    missing_reason: str,
):
    from application.instrument_selector import (
        RejectedInstrument,
    )

    found = {
        snapshot
        .ticker
        .upper()

        for snapshot
        in snapshots
    }

    missing = [
        RejectedInstrument(
            ticker=(
                ticker
                .strip()
                .upper()
            ),

            reason=(
                missing_reason
            ),
        )

        for ticker
        in requested_tickers

        if (
            ticker
            .strip()
            .upper()

            not in found
        )
    ]

    return (
        snapshots,

        missing,
    )


@app.get(
    "/api/instrument-selection/options"
)
def instrument_selection_options():
    from application.auto_portfolio_selector import (
        DESIRED_LEVELS,
        MIN_LEVELS,
    )
    from application.index_presets import (
        AUTO_UNIVERSE_TICKERS,
        INDEX_PRESETS,
    )

    return {
        "indexes": [
            {
                "index_id":
                    preset
                    .index_id,

                "name":
                    preset
                    .name,

                "description":
                    preset
                    .description,

                "tickers_count": (
                    len(
                        preset
                        .tickers
                    )
                ),

                "tickers": (
                    list(
                        preset
                        .tickers
                    )
                ),
            }

            for preset
            in INDEX_PRESETS
        ],

        "auto": {
            "universe_tickers_count": (
                len(
                    AUTO_UNIVERSE_TICKERS
                )
            ),
        },

        "defaults": {
            "desired_levels": (
                DESIRED_LEVELS
            ),

            "min_levels": (
                MIN_LEVELS
            ),

            "max_instruments": 5,

            "quantity": 1,
        },
    }


@app.post(
    "/api/instrument-selection/index"
)
def instrument_selection_index(
    request: (
        IndexSelectionRequest
    ),
):
    from application.auto_portfolio_selector import (
        IndexPortfolioSelector,
    )
    from application.index_presets import (
        find_index_preset,
    )

    preset = (
        find_index_preset(
            request.index_id,
        )
    )

    if (
        preset
        is None
    ):
        raise HTTPException(
            status_code=404,

            detail=(
                "Index not found: "
                f"{request.index_id}"
            ),
        )

    try:
        snapshots = (
            instrument_market_service
            .get_snapshots(
                tickers=(
                    list(
                        preset
                        .tickers
                    )
                ),

                trading_account_id=(
                    request
                    .trading_account_id
                ),
            )
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,

            detail=(
                str(error)
            ),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=502,

            detail=(
                "T-Invest market data "
                "failed: "
                f"{error!r}"
            ),
        ) from error

    api_usage_repository.record(
        source="web",

        operation=(
            "instrument_selection_index"
        ),

        weight=max(
            1,

            len(
                preset
                .tickers
            ),
        ),
    )

    (
        snapshots,

        missing_rejected,
    ) = (
        _snapshots_with_missing_rejected(
            snapshots=(
                snapshots
            ),

            requested_tickers=(
                list(
                    preset
                    .tickers
                )
            ),

            missing_reason=(
                "нет данных "
                "по инструменту"
            ),
        )
    )

    try:
        plan = (
            IndexPortfolioSelector()
            .select(
                snapshots=(
                    snapshots
                ),

                capital=(
                    request
                    .capital
                ),

                quantity=(
                    request
                    .quantity
                ),
            )
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,

            detail=(
                str(error)
            ),
        ) from error

    plan.rejected = (
        missing_rejected
        + plan.rejected
    )

    return (
        _grid_selection_plan_response(
            mode="index",

            index_id=(
                preset
                .index_id
            ),

            plan=plan,
        )
    )


@app.post(
    "/api/instrument-selection/auto"
)
def instrument_selection_auto(
    request: (
        AutoSelectionRequest
    ),
):
    from application.auto_portfolio_selector import (
        AutoPortfolioSelector,
    )
    from application.index_presets import (
        AUTO_UNIVERSE_TICKERS,
    )

    try:
        snapshots = (
            instrument_market_service
            .get_snapshots(
                tickers=(
                    list(
                        AUTO_UNIVERSE_TICKERS
                    )
                ),

                trading_account_id=(
                    request
                    .trading_account_id
                ),
            )
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,

            detail=(
                str(error)
            ),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=502,

            detail=(
                "T-Invest market data "
                "failed: "
                f"{error!r}"
            ),
        ) from error

    api_usage_repository.record(
        source="web",

        operation=(
            "instrument_selection_auto"
        ),

        weight=max(
            1,

            len(
                AUTO_UNIVERSE_TICKERS
            ),
        ),
    )

    (
        snapshots,

        missing_rejected,
    ) = (
        _snapshots_with_missing_rejected(
            snapshots=(
                snapshots
            ),

            requested_tickers=(
                list(
                    AUTO_UNIVERSE_TICKERS
                )
            ),

            missing_reason=(
                "нет данных "
                "по инструменту"
            ),
        )
    )

    try:
        plan = (
            AutoPortfolioSelector(
                desired_levels=(
                    request
                    .desired_levels
                ),

                min_levels=(
                    request
                    .min_levels
                ),
            )
            .select(
                snapshots=(
                    snapshots
                ),

                capital=(
                    request
                    .capital
                ),

                quantity=(
                    request
                    .quantity
                ),

                max_price=(
                    request
                    .max_price
                ),

                max_instruments=(
                    request
                    .max_instruments
                ),
            )
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,

            detail=(
                str(error)
            ),
        ) from error

    plan.rejected = (
        missing_rejected
        + plan.rejected
    )

    return (
        _grid_selection_plan_response(
            mode="auto",

            index_id=None,

            plan=plan,
        )
    )


# ============================================================
# SESSIONS
# ============================================================

@app.get(
    "/api/sessions"
)
def sessions():
    return {
        "sessions": [
            _build_display_session(
                web_session=session,
            )
            for session
            in session_registry
            .get_sessions()
        ],
    }


@app.get(
    "/api/session/{ticker}"
)
def session_detail(
    ticker: str,
):
    try:
        web_session = (
            session_registry
            .get_session(
                ticker=ticker,
            )
        )

    except KeyError as error:
        raise HTTPException(
            status_code=404,
            detail=(
                "Session not found: "
                f"{ticker.upper()}"
            ),
        ) from error

    return (
        _build_display_session(
            web_session=(
                web_session
            ),
        )
    )


# ============================================================
# SESSION CHART 1.2 (п. 2 плана)
# ============================================================

def _parse_trade_price(
    details: str,
) -> Decimal | None:
    marker = (
        "цена="
    )

    index = (
        details
        .find(
            marker
        )
    )

    if (
        index
        < 0
    ):
        return None

    tail = (
        details[
            index
            + len(
                marker
            ):
        ]
    )

    match = (
        re.match(
            r"-?\d+(?:\.\d+)?",

            tail
            .strip(),
        )
    )

    if (
        match
        is None
    ):
        return None

    try:
        return (
            Decimal(
                match
                .group(
                    0
                )
            )
        )

    except Exception:
        return None


def _resolve_chart_token(
    state,
) -> str | None:
    try:
        account = (
            trading_account_service
            .get(
                state
                .trading_account_id
            )
        )

        return (
            trading_account_service
            .get_credentials(
                account.id
            )
            .require(
                "token"
            )
        )

    except Exception:
        return (
            settings
            .tinvest_sandbox_token

            or (
                settings
                .tinvest_token
            )
        )


@app.get(
    "/api/session"
    "/{ticker}/chart"
)
def session_chart(
    ticker: str,

    days: int = 60,
):
    normalized = (
        ticker
        .upper()
    )

    safe_days = (
        max(
            7,

            min(
                days,
                365,
            ),
        )
    )

    state = None

    instrument_state = (
        None
    )

    for snapshot in (
        trading_state_repository
        .get_all()
    ):
        for (
            instrument
        ) in (
            snapshot
            .instruments
        ):
            if (
                instrument
                .ticker
                .upper()
                == normalized
            ):
                state = (
                    snapshot
                )

                instrument_state = (
                    instrument
                )

                break

        if (
            state
            is not None
        ):
            break

    candles = []

    if (
        state
        is not None
    ):
        token = (
            _resolve_chart_token(
                state
            )
        )

        if token:
            try:
                now = (
                    datetime
                    .now(
                        timezone.utc,
                    )
                )

                candles = (
                    TInvestHistoryProvider(
                        client_factory=(
                            TInvestClientFactory(
                                token=(
                                    token
                                ),
                            )
                        ),

                        mapper=(
                            TInvestCandlesMapper()
                        ),
                    )
                    .get_daily_candles(
                        instrument_id=(
                            instrument_state
                            .instrument_uid
                        ),

                        date_from=(
                            now
                            - timedelta(
                                days=(
                                    safe_days
                                )
                            )
                        ),

                        date_to=(
                            now
                        ),
                    )
                )

            except Exception as error:
                print(
                    "SESSION CHART CANDLES FAILED:",
                    repr(
                        error
                    ),
                )

    trades = []

    for (
        event
    ) in (
        operation_log_repository
        .recent(
            limit=500,
        )
    ):
        if (
            event
            .event_type
            not in {
                "BUY",
                "SELL",

                #
                # Точки истории движения
                # траллов (п. 2 плана).
                #
                "TRAILING",
            }
        ):
            continue

        if (
            (
                event
                .ticker
                or ""
            )
            .upper()
            != normalized
        ):
            continue

        price = (
            _parse_trade_price(
                event.details
            )
        )

        if (
            price
            is None
        ):
            continue

        trades.append(
            {
                "time":
                    event
                    .created_at,

                "side":
                    event
                    .event_type,

                "price":
                    str(
                        price
                    ),
            }
        )

    levels = []

    positions = []

    if (
        instrument_state
        is not None
    ):
        levels = [
            {
                "level_index":
                    level
                    .level_index,

                "price":
                    str(
                        level
                        .level_price
                    ),

                "status":
                    level
                    .status,
            }

            for level
            in (
                instrument_state
                .levels
            )
        ]

        positions = [
            {
                "level_index":
                    position
                    .level_index,

                "entry_price":
                    str(
                        position
                        .entry_price
                    ),

                "quantity":
                    position
                    .quantity,

                "trailing_exit_target_price": (
                    str(
                        position
                        .trailing_exit_target_price
                    )

                    if (
                        position
                        .trailing_exit_target_price
                        is not None
                    )

                    else None
                ),

                "trailing_exit_highest_price": (
                    str(
                        position
                        .trailing_exit_highest_price
                    )

                    if (
                        position
                        .trailing_exit_highest_price
                        is not None
                    )

                    else None
                ),
            }

            for position
            in (
                instrument_state
                .open_positions
            )
        ]

    return {
        "ticker":
            normalized,

        "session_id": (
            state
            .session_id

            if (
                state
                is not None
            )

            else None
        ),

        "candles": [
            {
                "time":
                    candle
                    .timestamp
                    .isoformat(),

                "open":
                    str(
                        candle
                        .open
                    ),

                "high":
                    str(
                        candle
                        .high
                    ),

                "low":
                    str(
                        candle
                        .low
                    ),

                "close":
                    str(
                        candle
                        .close
                    ),
            }

            for candle
            in candles
        ],

        "levels":
            levels,

        "positions":
            positions,

        "trades":
            trades,
    }


@app.post(
    "/api/stop-session/{ticker}"
)
def stop_session(
    ticker: str,
):
    web_runner_registry\
        .stop_by_ticker(
            ticker=ticker,
        )

    sandbox_session_registry\
        .unregister(
            ticker=ticker,
        )

    try:
        session = (
            session_registry
            .stop_session(
                ticker=ticker,
            )
        )

    except KeyError as error:
        raise HTTPException(
            status_code=404,
            detail=(
                "Session not found: "
                f"{ticker.upper()}"
            ),
        ) from error

    if session is None:
        return {
            "ticker":
                ticker.upper(),

            "status":
                "REMOVED",

            "removed":
                True,
        }

    return {
        **_build_display_session(
            web_session=session,
        ),

        "removed":
            False,
    }


# ============================================================
# DRAIN / «СУШКА»
# ============================================================

@app.post(
    "/api/drain-session/{ticker}"
)
def drain_session(
    ticker: str,
):
    normalized_ticker = (
        ticker.upper()
    )

    runners = (
        web_runner_registry
        .get_by_ticker(
            normalized_ticker
        )
    )

    if not runners:
        raise HTTPException(
            status_code=404,
            detail=(
                "Active runner not found: "
                f"{normalized_ticker}"
            ),
        )

    drained = (
        web_runner_registry
        .drain_by_ticker(
            normalized_ticker
        )
    )

    api_usage_repository.record(
        source="web",
        operation="session_drain_requested",
        weight=max(1, drained),
        ticker=normalized_ticker,
    )

    return {
        "ticker": normalized_ticker,
        "status": "DRAINING",
        "runners_affected": drained,
        "message": (
            "Текущая сетка продолжает работать штатно. "
            "Когда открытых позиций станет 0, "
            "сессия будет остановлена автоматически."
        ),
    }


# ============================================================
# RESUME / ОТМЕНА СУШКИ 1.2
# ============================================================

@app.post(
    "/api/resume-session/{ticker}"
)
def resume_session(
    ticker: str,
):
    normalized_ticker = (
        ticker.upper()
    )

    runners = (
        web_runner_registry
        .get_by_ticker(
            normalized_ticker
        )
    )

    if not runners:
        raise HTTPException(
            status_code=404,
            detail=(
                "Active runner not found: "
                f"{normalized_ticker}"
            ),
        )

    resumed = (
        web_runner_registry
        .resume_by_ticker(
            normalized_ticker
        )
    )

    api_usage_repository.record(
        source="web",
        operation="session_resume_requested",
        weight=max(1, resumed),
        ticker=normalized_ticker,
    )

    return {
        "ticker": normalized_ticker,
        "status": "RUNNING",
        "runners_affected": resumed,
        "message": (
            "Сушка отменена. Сессия продолжает "
            "работать в обычном режиме."
        ),
    }


# ============================================================
# START PLAN
# ============================================================

@app.post(
    "/api/start-plan"
)
def start_plan(
    request: StartPlanRequest,
):
    available_cash = (
        request.available_cash
        if request.available_cash
        is not None
        else Decimal("0")
    )

    account_id = (
        request.trading_account_id
    )

    if (
        account_id is None
    ):
        try:
            account_id = (
                _resolve_sandbox_trading_account(
                    None,
                )
                .id
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

    try:
        account = (
            trading_account_service
            .get(
                account_id
            )
        )

            credentials = (
                trading_account_service
                .get_credentials(
                    account.id
                )
            )

            adapter = (
                broker_registry
                .get(
                    account.broker
                )
            )

            portfolio = (
                adapter.get_portfolio(
                    credentials=credentials,
                    broker_account_id=(
                        account
                        .broker_account_id
                    ),
                    mode=account.mode,
                )
            )

            available_cash = (
                portfolio.cash
            )

        except KeyError as error:
            raise HTTPException(
                status_code=404,
                detail=(
                    "Trading account "
                    "not found"
                ),
            ) from error

        except Exception as error:
            raise HTTPException(
                status_code=502,
                detail=(
                    "Cannot read LIVE account "
                    f"cash: {error!r}"
                ),
            ) from error

    config = (
        _build_multi_instrument_config(
            instruments=(
                request.instruments
            ),
        )
    )

    prices_by_ticker: dict[
        str,
        Decimal,
    ] = {}

    price_ranges_by_ticker: dict[
        str,
        tuple[
            Decimal,
            Decimal,
        ],
    ] = {}

    for instrument in (
        request.instruments
    ):
        ticker = (
            instrument
            .ticker
            .upper()
        )

        current_price = (
            _get_mock_price(
                ticker=ticker,
            )
        )

        prices_by_ticker[
            ticker
        ] = current_price

        price_ranges_by_ticker[
            ticker
        ] = (
            current_price
            * Decimal(
                "0.70"
            ),

            current_price
            * Decimal(
                "1.10"
            ),
        )

    plan = (
        PortfolioOrchestrator()
        .build_start_plan(
            config=config,

            price_ranges_by_ticker=(
                price_ranges_by_ticker
            ),

            prices_by_ticker=(
                prices_by_ticker
            ),

            available_cash=(
                available_cash
            ),
        )
    )

    return {
        "available_cash":
            _format_money(
                plan
                .available_cash
            ),

        "total_required":
            _format_money(
                plan
                .total_required_deposit
            ),

        "remaining_cash":
            _format_money(
                plan
                .remaining_cash
            ),

        "missing_cash":
            _format_money(
                plan
                .missing_cash
            ),

        "can_start":
            plan.can_start,

        "can_start_forced":
            plan
            .can_start_forced,

        "capital_utilization_percent":
            _format_money(
                plan
                .capital_utilization_percent
            ),

        "instruments": [
            {
                "ticker":
                    instrument.ticker,

                "levels":
                    instrument
                    .levels_count,

                "quantity":
                    instrument.quantity,

                "last_price":
                    _format_money(
                        instrument
                        .last_price
                    ),

                "required_deposit":
                    _format_money(
                        instrument
                        .required_deposit
                    ),
            }
            for instrument
            in plan.instruments
        ],
    }


# ============================================================
# SANDBOX
# ============================================================

@app.post(
    "/api/start-sandbox"
)
def start_sandbox(
    request: StartSandboxRequest,
):
    started_sessions = [
        session_registry
        .start_session(
            ticker=(
                instrument.ticker
            ),

            levels=(
                instrument.levels
            ),

            quantity=(
                instrument.quantity
            ),
        )
        for instrument
        in request.instruments
    ]

    real_sandbox_status = (
        "disabled"
    )

    if (
        _is_real_sandbox_enabled()
    ):
        try:
            real_sandbox_status = (
                _try_start_real_sandbox(
                    request=request,
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
        "status":
            "started",

        "mode":
            "sandbox",

        "real_sandbox_status":
            real_sandbox_status,

        "force":
            request.force,

        "trading_account_id":
            request
            .trading_account_id,

        "sessions": [
            _build_display_session(
                web_session=session,
            )
            for session
            in started_sessions
        ],
    }


# ============================================================
# LIVE STATUS
# ============================================================

@app.get(
    "/api/live/status"
)
def live_status():
    status = (
        LiveAccountService(
            settings=settings,
        )
        .get_status()
    )

    return {
        "token_configured":
            status
            .token_configured,

        "selected_account_id":
            status
            .selected_account_id,

        "account_found":
            status
            .account_found,

        "live_trading_enabled":
            status
            .live_trading_enabled,

        "trading_mode":
            status
            .trading_mode,

        "accounts": [
            {
                "account_id":
                    account
                    .account_id,

                "name":
                    account.name,

                "status":
                    account.status,

                "account_type":
                    account
                    .account_type,

                "selected":
                    account.selected,
            }
            for account
            in status.accounts
        ],

        "portfolio": (
            {
                "total_amount_shares":
                    str(
                        status
                        .portfolio
                        .total_amount_shares
                    ),

                "total_amount_bonds":
                    str(
                        status
                        .portfolio
                        .total_amount_bonds
                    ),

                "total_amount_etf":
                    str(
                        status
                        .portfolio
                        .total_amount_etf
                    ),

                "total_amount_currencies":
                    str(
                        status
                        .portfolio
                        .total_amount_currencies
                    ),

                "expected_yield":
                    str(
                        status
                        .portfolio
                        .expected_yield
                    ),

                "positions_count":
                    status
                    .portfolio
                    .positions_count,
            }
            if (
                status.portfolio
                is not None
            )
            else None
        ),

        "unary_limits_count":
            status
            .unary_limits_count,

        "stream_limits_count":
            status
            .stream_limits_count,

        "error":
            status.error,
    }


# ============================================================
# REAL SANDBOX
# ============================================================

def _try_start_real_sandbox(
    request: StartSandboxRequest,
) -> str:
    try:
        config = (
            _build_multi_instrument_config(
                instruments=(
                    request.instruments
                ),
            )
        )

        sandbox_account = (
            _resolve_sandbox_trading_account(
                trading_account_id=(
                    request
                    .trading_account_id
                ),
            )
        )

        sandbox_token = (
            _require_account_token(
                account=(
                    sandbox_account
                ),
            )
        )

        sandbox_account_id = (
            sandbox_account
            .broker_account_id
        )

        broker_name = (
            sandbox_account
            .broker
            .value
        )

        context = (
            MultiInstrumentTradingSessionFactory(
                settings=settings,
                knowledge_engine=(
                    knowledge_engine
                ),

                operation_log=(
                    operation_log_service
                ),

                notifier=(
                    telegram_notifier
                ),
            )
            .create_sandbox_session(
                config=config,

                token=(
                    sandbox_token
                ),

                sandbox_account_id=(
                    sandbox_account_id
                ),
            )
        )

        runner_session_id = (
            _build_runner_session_id(
                mode="sandbox",

                broker_account_id=(
                    context.account_id
                ),

                instruments=(
                    request.instruments
                ),
            )
        )

        runner_session_id = (
            f"{broker_name}:"
            f"{sandbox_account.id}:"
            f"{runner_session_id}"
        )

        runner_session_id = (
            _uniquify_runner_session_id(
                runner_session_id
            )
        )

        trading_account_id = (
            sandbox_account
            .id
        )

        runner = (
            WebRunnerService(
                context=context,

                api_usage_repository=(
                    api_usage_repository
                ),

                reconciliation_journal=(
                    reconciliation_journal
                ),

                polling_interval_seconds=10,

                state_service=(
                    trading_state_service
                ),

                session_id=(
                    runner_session_id
                ),

                trading_account_id=(
                    trading_account_id
                ),

                auto_rebalance=(
                    _build_auto_rebalance_service(
                        request=(
                            request
                        ),

                        trading_account_id=(
                            trading_account_id
                        ),
                    )
                ),

                operation_log=(
                    operation_log_service
                ),
            )
        )

        web_runner_registry.start(
            runner=runner,
        )

        return (
            "started"
        )

    except ValueError:
        raise

    except Exception as error:
        print(
            "REAL SANDBOX START FAILED:",
            repr(
                error
            ),
        )

        return (
            "fallback_mock"
        )


def _resolve_sandbox_trading_account(
    trading_account_id: (
        str | None
    ),
) -> TradingAccount:
    if (
        trading_account_id
        is not None
    ):
        try:
            account = (
                trading_account_service
                .get(
                    trading_account_id
                )
            )

        except KeyError as error:
            raise ValueError(
                "Trading account "
                "not found"
            ) from error

    else:
        candidates = [
            account
            for account
            in trading_account_service
            .get_enabled()
            if account.broker
            == BrokerType.TINVEST
            and account.mode
            == TradingAccountMode.SANDBOX
        ]

        if not candidates:
            raise ValueError(
                "No enabled SANDBOX "
                "trading account: "
                "add a T-Invest "
                "SANDBOX account "
                "in Settings"
            )

        account = candidates[0]

    if not account.enabled:
        raise ValueError(
            "Trading account "
            "is disabled"
        )

    if (
        account.broker
        != BrokerType.TINVEST
    ):
        raise ValueError(
            "Sandbox trading for "
            f"{account.broker.value} "
            "is not supported yet"
        )

    if (
        account.mode
        != TradingAccountMode.SANDBOX
    ):
        raise ValueError(
            "Selected account "
            "is not SANDBOX"
        )

    return account


def _require_account_token(
    account: TradingAccount,
) -> str:
    try:
        return (
            trading_account_service
            .get_credentials(
                account.id
            )
            .require(
                "token"
            )
        )

    except Exception as error:
        raise ValueError(
            "Failed to get token "
            "for trading account "
            f"'{account.name}': "
            f"{error}"
        ) from error


# ============================================================
# HELPERS
# ============================================================

def _format_money(
    value: Decimal,
) -> str:
    return (
        str(
            value
            .quantize(
                Decimal(
                    "0.01"
                ),

                rounding=(
                    ROUND_HALF_UP
                ),
            )
        )
    )


def _trading_account_to_dict(
    account: TradingAccount,
) -> dict:
    return {
        "id":
            account.id,

        "name":
            account.name,

        "broker":
            account
            .broker
            .value,

        "broker_account_id":
            account
            .broker_account_id,

        "mode":
            account
            .mode
            .value,

        "credentials_configured":
            True,

        "commission_mode":
            account
            .commission_mode
            .value,

        "custom_buy_commission_percent": (
            str(
                account
                .custom_buy_commission_percent
            )
            if (
                account
                .custom_buy_commission_percent
                is not None
            )
            else None
        ),

        "custom_sell_commission_percent": (
            str(
                account
                .custom_sell_commission_percent
            )
            if (
                account
                .custom_sell_commission_percent
                is not None
            )
            else None
        ),

        "detected_buy_commission_percent": (
            str(
                account
                .detected_buy_commission_percent
            )
            if (
                account
                .detected_buy_commission_percent
                is not None
            )
            else None
        ),

        "detected_sell_commission_percent": (
            str(
                account
                .detected_sell_commission_percent
            )
            if (
                account
                .detected_sell_commission_percent
                is not None
            )
            else None
        ),

        "expected_buy_commission_percent":
            str(
                account
                .get_expected_buy_commission_percent()
            ),

        "expected_sell_commission_percent":
            str(
                account
                .get_expected_sell_commission_percent()
            ),

        "enabled":
            account.enabled,

        "created_at": (
            account
            .created_at
            .isoformat()
            if (
                account.created_at
                is not None
            )
            else None
        ),

        "updated_at": (
            account
            .updated_at
            .isoformat()
            if (
                account.updated_at
                is not None
            )
            else None
        ),
    }


def _build_broker_info(
    broker: BrokerType,
    supported: bool,
) -> dict:
    if (
        broker
        == BrokerType.TINVEST
    ):
        return {
            "id":
                broker.value,

            "name":
                "T-Invest",

            "supported":
                supported,

            "credential_fields": [
                {
                    "key":
                        "token",

                    "label":
                        "API Token",

                    "type":
                        "password",

                    "required":
                        True,
                },
            ],

            "modes": [
                "live",
                "sandbox",
            ],
        }

    names = {
        BrokerType.ALFA:
            "Альфа-Инвестиции",

        BrokerType.BCS:
            "БКС",

        BrokerType.FINAM:
            "Финам",

        BrokerType.OTHER:
            "Другой брокер",
    }

    return {
        "id":
            broker.value,

        "name":
            names.get(
                broker,
                broker.value,
            ),

        "supported":
            supported,

        "credential_fields":
            [],

        "modes": [
            "live",
        ],
    }


def _broker_portfolio_to_dict(
    portfolio,
) -> dict:
    return {
        "cash":
            str(
                portfolio.cash
            ),

        "total_value": (
            str(
                portfolio
                .total_value
            )
            if (
                portfolio
                .total_value
                is not None
            )
            else None
        ),

        "positions_count":
            portfolio
            .positions_count,
    }


def _build_multi_instrument_config(
    instruments: list[
        StartPlanInstrumentRequest
    ],
) -> MultiInstrumentSessionConfig:
    return (
        MultiInstrumentSessionConfig(
            instruments=[
                InstrumentConfig(
                    ticker=(
                        instrument
                        .ticker
                        .upper()
                    ),

                    levels_count=(
                        instrument.levels
                    ),

                    quantity=(
                        instrument.quantity
                    ),
                )
                for instrument
                in instruments
            ],
        )
    )


def _build_auto_rebalance_service(
    request: StartSandboxRequest,

    trading_account_id: (
        str | None
    ),
) -> (
    AutoRebalanceService
    | None
):
    if (
        not (
            request
            .auto_rebalance
        )
    ):
        return None

    return (
        AutoRebalanceService(
            market_service=(
                instrument_market_service
            ),

            instrument_manager=(
                SessionInstrumentManager(
                    knowledge_engine=(
                        knowledge_engine
                    ),

                    operation_log=(
                        operation_log_service
                    ),
                )
            ),

            max_price=(
                request
                .max_price
            ),

            max_instruments=(
                request
                .max_instruments
            ),

            trading_account_id=(
                trading_account_id
            ),
        )
    )


def _build_runner_session_id(
    mode: str,

    broker_account_id: str,

    instruments: list[
        StartPlanInstrumentRequest
    ],
) -> str:
    normalized_instruments = [
        {
            "ticker":
                instrument
                .ticker
                .upper(),

            "levels":
                int(
                    instrument.levels
                ),

            "quantity":
                int(
                    instrument.quantity
                ),
        }
        for instrument
        in instruments
    ]

    normalized_instruments.sort(
        key=lambda item: (
            item[
                "ticker"
            ],

            item[
                "levels"
            ],

            item[
                "quantity"
            ],
        ),
    )

    payload = {
        "mode":
            mode.lower(),

        "broker_account_id":
            str(
                broker_account_id
            ),

        "instruments":
            normalized_instruments,
    }

    serialized = (
        json.dumps(
            payload,

            ensure_ascii=False,

            sort_keys=True,

            separators=(
                ",",
                ":",
            ),
        )
    )

    digest = (
        hashlib
        .sha256(
            serialized
            .encode(
                "utf-8"
            )
        )
        .hexdigest()[:20]
    )

    return (
        f"{mode.lower()}:"
        f"{broker_account_id}:"
        f"{digest}"
    )


def _build_trading_account_id(
    mode: str,
    broker_account_id: str,
) -> str:
    return (
        f"{mode.lower()}:"
        f"{broker_account_id}"
    )


def _uniquify_runner_session_id(
    session_id: str,
) -> str:
    if not web_runner_registry.has_session_id(
        session_id
    ):
        return session_id

    counter = 2

    while True:
        candidate = (
            f"{session_id}"
            f"#{counter}"
        )

        if not web_runner_registry.has_session_id(
            candidate
        ):
            return candidate

        counter += 1


def _is_real_sandbox_enabled() -> bool:
    if (
        os.getenv(
            "PYTEST_CURRENT_TEST"
        )
    ):
        return False

    return (
        settings
        .web_real_sandbox
    )


def _build_display_session(
    web_session: WebSession,
):
    snapshot = (
        sandbox_session_registry
        .build_snapshot(
            ticker=(
                web_session
                .ticker
            ),
        )
    )

    if snapshot is not None:
        result = (
            _snapshot_to_dict(
                snapshot=snapshot,
                web_session=(
                    web_session
                ),
            )
        )
    else:
        result = (
            _web_session_to_dict(
                session=(
                    web_session
                ),
            )
        )

    # Surface runner lifecycle in the existing session UI.
    # Until sessions become fully account/session_id-addressable,
    # DRAINING has priority for a matching ticker.
    runners = (
        web_runner_registry
        .get_by_ticker(
            web_session.ticker
        )
    )

    if any(
        getattr(
            runner,
            "lifecycle_status",
            "RUNNING",
        )
        == "DRAINING"
        for runner in runners
    ):
        result["status"] = "DRAINING"

    return result


def _snapshot_to_dict(
    snapshot: SandboxSessionSnapshot,

    web_session: WebSession,
):
    display_quantity = (
        snapshot.quantity
    )

    if (
        display_quantity
        == 0
    ):
        display_quantity = (
            web_session.quantity
        )

    return {
        "ticker":
            snapshot.ticker,

        "levels":
            web_session.levels,

        "quantity":
            display_quantity,

        "status":
            snapshot.status,

        "positions":
            snapshot.positions,

        "current_price":
            float(
                snapshot
                .current_price
            ),

        "realized_profit":
            float(
                snapshot
                .realized_profit
            ),

        "unrealized_profit":
            float(
                snapshot
                .unrealized_profit
            ),

        "total_profit":
            float(
                snapshot
                .total_profit
            ),
    }


def _web_session_to_dict(
    session: WebSession,
):
    return {
        "ticker":
            session.ticker,

        "levels":
            session.levels,

        "quantity":
            session.quantity,

        "status":
            session.status,

        "positions":
            session.positions,

        "current_price":
            session
            .current_price,

        "realized_profit":
            session
            .realized_profit,

        "unrealized_profit":
            session
            .unrealized_profit,

        "total_profit":
            session
            .total_profit,
    }


def _get_mock_price(
    ticker: str,
) -> Decimal:
    prices = {
        "SBER":
            Decimal(
                "317"
            ),

        "GAZP":
            Decimal(
                "107"
            ),

        "LKOH":
            Decimal(
                "4453"
            ),

        "VTBR":
            Decimal(
                "0.09"
            ),
    }

    return (
        prices.get(
            ticker,

            Decimal(
                "100"
            ),
        )
    )
