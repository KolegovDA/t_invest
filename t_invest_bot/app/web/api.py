from __future__ import annotations

import hashlib
import hmac
from urllib.parse import urlsplit
import json
import os
import re
import threading
import time

from contextlib import asynccontextmanager
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from decimal import Decimal, ROUND_HALF_UP

from fastapi import (
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
)
from fastapi.middleware.cors import (
    CORSMiddleware,
)
from fastapi.responses import (
    JSONResponse,
)
from pydantic import (
    BaseModel,
    Field,
)

from notifications.notifier import (
    CompositeNotifier,
    Notifier,
)
from notifications.ntfy_notifier import (
    NtfyNotifier,
)
from notifications.vapid_keys import (
    load_or_create_vapid_keys,
)
from notifications.webpush_notifier import (
    WebPushNotifier,
    validate_push_endpoint,
)

from application.live_account_service import (
    LiveAccountService,
)
from application.account_performance_service import (
    AccountPerformanceService,
)

from application.auth_service import (
    AuthService,
    hash_password,
)

from application.head_server_client import (
    HeadReplicationWorker,
    HeadServerClient,
    HeadSyncPayloadBuilder,
)

from application.topup_service import (
    TopupService,
)
from application.trading_settings_service import TradingSettingsService

from application.auto_rebalance_service import (
    AutoRebalanceService,
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
from application.balance_backfill_service import (
    BalanceBackfillService,
    EXTERNAL_FLOW_KINDS,
)
from application.equity_history_service import (
    EquityHistoryService,
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
from application.bybit_session_factory import BybitSessionFactory
from application.operation_log_service import (
    OperationLogService,
)

from application.commission_service import (
    CommissionService,
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
from application.platform_connection_service import (
    PlatformConnectionService,
)
from application.session_instrument_manager import (
    SessionInstrumentManager,
)
from application.trading_account_service import (
    BYBIT_DEFAULT_BASE_CURRENCY,
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
    get_data_directory,
    get_database_path,
)
from config.settings import (
    Settings,
)

from domain.balance_snapshot import (
    BalanceSnapshot,
)
from domain.broker_cash_flow import (
    BrokerCashFlow,
)
from domain.money_movement import (
    MoneyMovement,
)
from domain.platform_connection import (
    PlatformConnection,
)
from domain.trading_account import (
    BrokerType,
    CommissionMode,
    TradingAccount,
    TradingAccountMode,
)

from infrastructure.brokers.base import AssetRulesProvider
from infrastructure.brokers.default_registry import (
    create_default_broker_registry,
)
from infrastructure.security.dpapi_secret_protector import (
    DPAPISecretProtector,
)
from infrastructure.sqlite.account_backfill_repository import (
    SQLiteAccountBackfillRepository,
)
from infrastructure.sqlite.api_usage_repository import (
    SQLiteApiUsageRepository,
)
from infrastructure.sqlite.balance_snapshot_repository import (
    SQLiteBalanceSnapshotRepository,
)
from infrastructure.sqlite.broker_cash_flow_repository import (
    SQLiteBrokerCashFlowRepository,
)
from infrastructure.sqlite.commission_repository import (
    SQLiteCommissionRepository,
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
from infrastructure.sqlite.platform_connection_repository import (
    PlatformConnectionRepository,
)
from infrastructure.sqlite.push_subscription_repository import (
    PushSubscriptionRepository,
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
from infrastructure.sqlite.user_topup_repository import (
    UserTopupRepository,
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


from app_version import (
    APP_VERSION,
)


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

        operation_log=(
            operation_log_service
        ),
    )
)


# ============================================================
# COMMISSION v1.3 (п. 1)
# ============================================================

commission_repository = (
    SQLiteCommissionRepository(
        database=database,
    )
)


commission_service = (
    CommissionService(
        repository=(
            commission_repository
        ),

        operation_log=(
            operation_log_service
        ),
    )
)


trading_settings_service = TradingSettingsService(db_path=str(database_path))


# ============================================================
# MONEY MOVEMENTS + PERFORMANCE 1.2 (пп. 4-5)
# ============================================================

money_movement_repository = (
    SQLiteMoneyMovementRepository(
        database=database,
    )
)


balance_snapshot_repository = (
    SQLiteBalanceSnapshotRepository(
        database=database,
    )
)

account_backfill_repository = (
    SQLiteAccountBackfillRepository(
        database=database,
    )
)

broker_cash_flow_repository = (
    SQLiteBrokerCashFlowRepository(
        database=database,
    )
)

balance_backfill_service = (
    BalanceBackfillService(
        snapshot_repository=(
            balance_snapshot_repository
        ),

        backfill_repository=(
            account_backfill_repository
        ),

        broker_cash_flow_repository=(
            broker_cash_flow_repository
        ),
    )
)


equity_history_service = (
    EquityHistoryService(
        operation_log_repository=(
            operation_log_repository
        ),

        money_movement_repository=(
            money_movement_repository
        ),

        broker_cash_flow_repository=(
            broker_cash_flow_repository
        ),
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


if (
    head_server_client
    is not None
):
    print(
        "[HEAD] Репликация "
        "включена:",

        settings
        .head_server_url,
    )

else:
    print(
        "[HEAD] Репликация "
        "ОТКЛЮЧЕНА "
        "(HEAD_SERVER_ENABLED"
        "=false)",
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


platform_connection_repository = (
    PlatformConnectionRepository(
        db_path=str(
            database_path
        ),
    )
)


platform_connection_service = (
    PlatformConnectionService(
        repository=(
            platform_connection_repository
        ),

        secret_protector=(
            DPAPISecretProtector()
        ),
    )
)


trading_account_service.platform_connection_service = platform_connection_service


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
        balance_snapshot_repository=balance_snapshot_repository,
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

        commission_repository=(
            commission_repository
        ),

        commission_service=(
            commission_service
        ),

        trading_settings_service=trading_settings_service,

        operation_log_repository=(
            operation_log_repository
        ),
    )
)


# ============================================================
# BROKER REGISTRY
# ============================================================

broker_registry = (
    create_default_broker_registry()
)
head_sync_payload_builder.broker_registry = broker_registry


# ============================================================
# PUSH NOTIFICATIONS 1.2 (п. 3)
# ============================================================

#
# Каналы пуш-уведомлений (B3):
#
# 1) Web Push (VAPID) — основной
#    канал: браузерные подписки
#    из PWA-интерфейса. Работает
#    на iOS 16.4+ (PWA добавлена
#    на главный экран) и Android.
#    VAPID-пара генерируется
#    автоматически и хранится
#    в data/webpush_vapid.json.
#
# 2) ntfy — резервный канал:
#    NTFY_TOPIC (и опционально
#    NTFY_SERVER_URL) в настройках
#    сервера. Не задан топик —
#    канал отключён.
#
push_subscription_repository = (
    PushSubscriptionRepository(
        db_path=str(
            database_path
        ),
    )
)

vapid_keys = (
    load_or_create_vapid_keys(
        data_directory=(
            get_data_directory()
        ),
    )
)

webpush_notifier = (
    WebPushNotifier(
        subscription_source=(
            push_subscription_repository
        ),

        private_pem=(
            vapid_keys
            .private_pem
        ),
    )
)

push_notifiers: list[Notifier] = [
    webpush_notifier,
]

if (
    settings
    .ntfy_topic
):
    push_notifiers.append(
        NtfyNotifier(
            topic=(
                settings
                .ntfy_topic
            ),

            server_url=(
                settings
                .ntfy_server_url

                or "https://ntfy.sh"
            ),
        )
    )

push_notifier = (
    CompositeNotifier(
        notifiers=(
            push_notifiers
        ),
    )
)


# ============================================================
# TOPUPS B4 (п. 2): пополнение баланса ЛК через голову
# ============================================================

user_topup_repository = (
    UserTopupRepository(
        db_path=str(
            database_path
        ),
    )
)


topup_service = (
    TopupService(
        repository=(
            user_topup_repository
        ),

        commission_repository=(
            commission_repository
        ),

        head_client=(
            head_server_client
        ),

        user_repository=(
            user_repository
        ),

        operation_log=(
            operation_log_service
        ),

        notifier=(
            push_notifier
        ),
    )
)


head_replication_worker\
    .topup_service = (
        topup_service
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
                    push_notifier
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
        platform_connection_service=platform_connection_service,
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
        trading_settings_service=trading_settings_service,
        commission_service=commission_service,
        operation_log=operation_log_service,
        knowledge_engine=knowledge_engine,
        notifier=push_notifier,
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
        platform_connection_service.recover_from_sessions(
            states=trading_state_repository.get_active(),
            account_service=trading_account_service,
            legacy_token=settings.tinvest_token,
            legacy_account_id=settings.tinvest_live_account_id,
        )
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
    base_order_amount: Decimal | None = None


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

    bybit_automatic: bool = False

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


class PasswordResetRequest(
    BaseModel
):
    login: str

    code: str

    password: str

    device_id: str = (
        "web"
    )


class ProfileUpdateRequest(
    BaseModel
):
    full_name: (
        str | None
    ) = None

    phone: (
        str | None
    ) = None

    email: (
        str | None
    ) = None

    birth_date: (
        str | None
    ) = None


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

    broker_account_id: str = ""

    credentials: (
        dict[
            str,
            str,
        ]
        | None
    ) = None

    platform_id: (
        str | None
    ) = None

    mode: TradingAccountMode = (
        TradingAccountMode.LIVE
    )

    base_currency: (
        str | None
    ) = None

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

    base_currency: (
        str
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


class CreatePlatformConnectionRequest(
    BaseModel
):
    broker: BrokerType = (
        BrokerType.TINVEST
    )

    mode: TradingAccountMode = (
        TradingAccountMode.LIVE
    )

    credentials: dict[
        str,
        str,
    ]


class UpdatePlatformConnectionRequest(
    BaseModel
):
    credentials: dict[
        str,
        str,
    ]


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
# PLATFORMS (B2: подключение платформы
# без выбора счёта)
# ============================================================

def _platform_connection_to_dict(
    platform: PlatformConnection,
) -> dict:
    return {
        "id":
            platform.id,

        "broker":
            platform
            .broker
            .value,

        "mode":
            platform
            .mode
            .value,

        "credentials_configured":
            True,

        "created_at": (
            platform
            .created_at
            .isoformat()

            if (
                platform
                .created_at
                is not None
            )

            else None
        ),

        "updated_at": (
            platform
            .updated_at
            .isoformat()

            if (
                platform
                .updated_at
                is not None
            )

            else None
        ),
    }


@app.get(
    "/api/platforms"
)
def get_platform_connections():
    platforms = (
        platform_connection_service
        .get_all()
    )

    return {
        "platforms": [
            _platform_connection_to_dict(
                platform
            )

            for platform
            in platforms
        ],
    }


@app.post(
    "/api/platforms",
    status_code=201,
)
def create_platform_connection(
    request: (
        CreatePlatformConnectionRequest
    ),
):
    if request.mode != TradingAccountMode.LIVE:
        raise HTTPException(status_code=400, detail="Новые подключения доступны только в боевом режиме")
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
        platform = (
            platform_connection_service
            .connect(
                broker=(
                    request
                    .broker
                ),

                mode=(
                    request
                    .mode
                ),

                credentials=(
                    request
                    .credentials
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

    api_usage_repository.record(
        source="web",

        operation=(
            "platform_connected"
        ),

        weight=1,
    )

    operation_log_service.record(
        event_type=(
            "PLATFORM_CONNECTED"
        ),

        details=(
            "broker="
            f"{platform.broker.value} "

            "mode="
            f"{platform.mode.value}"
        ),
    )

    return (
        _platform_connection_to_dict(
            platform
        )
    )


@app.put(
    "/api/platforms/{platform_id}"
)
def update_platform_connection(
    platform_id: str,

    request: (
        UpdatePlatformConnectionRequest
    ),
):
    try:
        platform = (
            platform_connection_service
            .update_credentials(
                platform_id=(
                    platform_id
                ),

                credentials=(
                    request
                    .credentials
                ),
            )
        )

    except KeyError as error:
        raise HTTPException(
            status_code=404,

            detail=(
                "Platform connection "
                "not found"
            ),
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
            "PLATFORM_UPDATED"
        ),

        details=(
            "broker="
            f"{platform.broker.value} "

            "mode="
            f"{platform.mode.value}"
        ),
    )

    return (
        _platform_connection_to_dict(
            platform
        )
    )


@app.delete(
    "/api/platforms/{platform_id}"
)
def delete_platform_connection(
    platform_id: str,
):
    try:
        (
            platform_connection_service
            .delete(
                platform_id
            )
        )

    except KeyError as error:
        raise HTTPException(
            status_code=404,

            detail=(
                "Platform connection "
                "not found"
            ),
        ) from error

    return {
        "deleted": True,
    }


@app.post(
    "/api/platforms/{platform_id}/discover"
)
def discover_platform_accounts(
    platform_id: str,
):
    try:
        platform = (
            platform_connection_service
            .get(
                platform_id
            )
        )

        credentials_values = (
            platform_connection_service
            .get_credentials(
                platform_id
            )
        )

    except KeyError as error:
        raise HTTPException(
            status_code=404,

            detail=(
                "Platform connection "
                "not found"
            ),
        ) from error

    try:
        adapter = (
            broker_registry
            .get(
                platform
                .broker
            )
        )

    except KeyError as error:
        raise HTTPException(
            status_code=400,

            detail=(
                "Broker adapter is not available: "

                f"{platform.broker.value}"
            ),
        ) from error

    credentials = (
        TradingAccountCredentials(
            values=(
                credentials_values
            ),
        )
    )

    try:
        discovered = (
            _discover_broker_accounts_with_adapter(
                adapter=adapter,

                credentials=(
                    credentials
                ),

                mode=(
                    platform
                    .mode
                ),
            )
        )

    except Exception as error:
        return {
            "success": False,

            "platform_id":
                platform_id,

            "accounts": [],

            "error": repr(
                error
            ),
        }

    existing = {
        (
            account
            .broker
            .value,

            account
            .mode
            .value,

            account
            .broker_account_id,
        )

        for account
        in trading_account_service
        .get_all()
    }

    for item in discovered:
        item[
            "already_added"
        ] = (
            (
                platform
                .broker
                .value,

                platform
                .mode
                .value,

                item[
                    "broker_account_id"
                ],
            )

            in existing
        )

    api_usage_repository.record(
        source="web",

        operation=(
            "platform_accounts_discovered"
        ),

        weight=1,
    )

    return {
        "success": True,

        "platform_id":
            platform_id,

        "accounts":
            discovered,

        "error": None,
    }


# ============================================================
# WEB PUSH (B3: подписки браузерных
# пуш-уведомлений)
# ============================================================

class PushSubscribeRequest(
    BaseModel,
):
    endpoint: str

    keys: dict[str, str]


def _push_identity(request: Request, mutate: bool = False):
    user, token = _auth_user(request)
    session = auth_service.repository.get_session(token)
    if session is None or session.user_id != user.id:
        raise HTTPException(status_code=401, detail="Сессия истекла, войдите заново")
    csrf_token = hmac.new(token.encode(), b"esm-web-push-csrf", hashlib.sha256).hexdigest()
    if request.headers.get("Sec-Fetch-Site") == "cross-site":
        raise HTTPException(status_code=403, detail="Cross-site push request rejected")
    origin = request.headers.get("Origin")
    if origin:
        try:
            parsed = urlsplit(origin)
        except ValueError:
            raise HTTPException(status_code=403, detail="Invalid push request origin") from None
        if parsed.netloc != request.url.netloc or parsed.scheme != request.url.scheme:
            raise HTTPException(status_code=403, detail="Cross-origin push request rejected")
    if mutate:
        if not hmac.compare_digest(request.headers.get("X-ESM-CSRF", "").encode(), csrf_token.encode()):
            raise HTTPException(status_code=403, detail="Invalid CSRF token")
    return user.id, session.device_id, csrf_token


def _validated_push_endpoint(endpoint: str) -> str:
    try:
        return validate_push_endpoint(endpoint)
    except ValueError:
        raise HTTPException(status_code=400, detail="Unsupported push endpoint") from None


@app.get("/api/push/vapid-key")
def get_push_vapid_key(request: Request, response: Response):
    _, _, csrf_token = _push_identity(request)
    response.headers["Cache-Control"] = "no-store"
    return {"public_key": vapid_keys.public_key, "csrf_token": csrf_token}


@app.post(
    "/api/push/subscribe",
    status_code=201,
)
def subscribe_to_push(
    request: (
        PushSubscribeRequest
    ),
    http_request: Request,
):
    user_id, device_id, _ = _push_identity(http_request, mutate=True)
    endpoint = (
        request
        .endpoint
        .strip()
    )

    if (
        not endpoint
    ):
        raise HTTPException(
            status_code=400,

            detail=(
                "endpoint is required"
            ),
        )

    subscription = {
        "endpoint": (
            endpoint
        ),

        "keys": (
            request
            .keys
        ),
    }

    subscription["endpoint"] = _validated_push_endpoint(endpoint)
    if not request.keys.get("p256dh") or not request.keys.get("auth"):
        raise HTTPException(status_code=400, detail="Push encryption keys are required")
    try:
        push_subscription_repository.save(subscription, user_id, device_id)
    except ValueError:
        raise HTTPException(status_code=409, detail="Push subscription belongs to another device") from None

    return {
        "status":
            "subscribed",
    }


@app.delete(
    "/api/push/subscribe"
)
def unsubscribe_from_push(
    endpoint: str,
    request: Request,
):
    user_id, device_id, _ = _push_identity(request, mutate=True)
    push_subscription_repository.delete(_validated_push_endpoint(endpoint), user_id, device_id)

    return {
        "status":
            "unsubscribed",
    }


class PushTestRequest(BaseModel):
    endpoint: str | None = None


@app.post(
    "/api/push/test"
)
def send_test_push(http_request: Request, request: PushTestRequest | None = None):
    user_id, device_id, _ = _push_identity(http_request, mutate=True)
    endpoint = request.endpoint if request is not None else None
    if not endpoint:
        raise HTTPException(status_code=400, detail="Push endpoint is required")
    endpoint = _validated_push_endpoint(endpoint)
    subscriptions = push_subscription_repository.get_all(user_id, device_id)
    if not any(item.get("endpoint") == endpoint for item in subscriptions):
        raise HTTPException(status_code=409, detail="Нет сохранённой push-подписки этого устройства")
    report = webpush_notifier.notify("Тестовое push-уведомление: ESM Trade", endpoint=endpoint)
    if not isinstance(report, dict):
        raise HTTPException(status_code=502, detail="Push-сервис не подтвердил приём уведомления")
    if report["attempted"] == 0:
        raise HTTPException(status_code=409, detail="Нет сохранённых push-подписок. Включите уведомления на этом устройстве.")
    if report and report["accepted"] == 0:
        raise HTTPException(status_code=502, detail="Push-сервис не принял уведомление. Проверьте доступ сервера к push-сервисам и обновите подписку.")
    return {"status": "accepted", "delivery": report, "note": "Принято push-сервисом; показ на устройстве ещё не подтверждён"}


# ============================================================
# ACCOUNTS
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
    if request.mode != TradingAccountMode.LIVE:
        raise HTTPException(status_code=400, detail="Новые счета доступны только в боевом режиме; существующие sandbox-счета сохранены")
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

    #
    # B2: счёт добавляется
    # поверх подключённой
    # платформы — реквизиты
    # берутся из подключения.
    #
    credentials = (
        request.credentials
    )

    if (
        request.platform_id
        is not None
    ):
        try:
            platform = (
                platform_connection_service
                .get(
                    request
                    .platform_id
                )
            )

            platform_credentials = (
                platform_connection_service
                .get_credentials(
                    request
                    .platform_id
                )
            )

        except KeyError as error:
            raise HTTPException(
                status_code=404,

                detail=(
                    "Platform connection "
                    "not found"
                ),
            ) from error

        if (
            platform.broker
            != request.broker
        ):
            raise HTTPException(
                status_code=400,

                detail=(
                    "Platform broker does "
                    "not match the account "
                    "broker"
                ),
            )

        if (
            platform.mode
            != request.mode
        ):
            raise HTTPException(
                status_code=400,

                detail=(
                    "Platform mode does "
                    "not match the account "
                    "mode"
                ),
            )

        credentials = (
            platform_credentials
        )
        if request.broker == BrokerType.BYBIT:
            discovered = broker_registry.get(request.broker).get_accounts(
                TradingAccountCredentials(values=credentials), request.mode,
            )
            if len(discovered) != 1:
                raise HTTPException(status_code=400, detail="Не удалось однозначно определить счёт Bybit из подключения")
            request.broker_account_id = discovered[0].broker_account_id
            request.commission_mode = CommissionMode.AUTO
            request.custom_buy_commission_percent = None
            request.custom_sell_commission_percent = None

    elif not credentials:
        raise HTTPException(
            status_code=400,

            detail=(
                "Credentials or "
                "platform_id are "
                "required"
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
                    credentials
                ),

                mode=request.mode,

                base_currency=(
                    request
                    .base_currency
                ),

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

    if (
        account.enabled
        and account.mode
        == TradingAccountMode.LIVE
    ):
        threading.Thread(
            target=(
                _balance_backfill_account
            ),

            args=(
                account,
            ),

            daemon=(
                True
            ),

            name=(
                "balance-backfill-hook"
            ),
        ).start()

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
        discovered = (
            _discover_broker_accounts_with_adapter(
                adapter=adapter,

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


def _discover_broker_accounts_with_adapter(
    adapter,

    credentials: (
        TradingAccountCredentials
    ),

    mode: TradingAccountMode,
) -> list[dict]:
    accounts = (
        adapter.get_accounts(
            credentials=(
                credentials
            ),

            mode=mode,
        )
    )

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

                    mode=mode,
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

    return discovered


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

                base_currency=(
                    request
                    .base_currency
                ),

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

def _ensure_commission_allows_start(
) -> None:
    """
    v1.3: отрицательный
    ЛК-баланс включает
    «принудительную сушку» —
    новые сетки и инструменты
    запрещены, существующие
    дорабатывают и закрываются.
    """

    api_key = head_replication_worker._current_api_key()
    if api_key and head_server_client is not None:
        try:
            config = head_server_client.fetch_config(api_key=api_key)
            if config is not None:
                commission_service.apply_head_config(config)
        except Exception:
            pass
    try:
        forced_drain = commission_service.is_forced_drain()
    except Exception as error:
        raise HTTPException(status_code=503, detail="Не удалось проверить разрешение запуска") from error

    if forced_drain:
        raise HTTPException(
            status_code=403,

            detail=(
                "ЛК-баланс отрицательный: "
                "запуск новых сеток запрещён "
                "(принудительная сушка). "
                "Существующие сетки продолжат "
                "работу и закроются сами."
            ),
        )


def _start_bybit(request: StartSandboxRequest, account):
    if account.mode != TradingAccountMode.LIVE or not account.enabled:
        raise HTTPException(status_code=400, detail="Выберите активный боевой счёт Bybit")
    config = _build_multi_instrument_config(request.instruments, "bybit")
    credentials = trading_account_service.get_credentials(account.id)
    context = BybitSessionFactory(
        operation_log=operation_log_service, notifier=push_notifier,
        commission_service=commission_service, knowledge_engine=knowledge_engine,
    ).create(config, credentials, account.broker_account_id, account.id, (account.base_currency or "USDT").upper(), request.bybit_automatic)
    runner_id = _uniquify_runner_session_id(f"bybit:{account.id}:" + _build_runner_session_id("live", context.account_id, request.instruments))
    runner = WebRunnerService(
        context=context, api_usage_repository=api_usage_repository,
        reconciliation_journal=reconciliation_journal, state_service=trading_state_service,
        session_id=runner_id, trading_account_id=account.id,
        operation_log=operation_log_service, commission_service=commission_service,
        polling_interval_seconds=10, lifecycle_status="RUNNING",
    )
    web_runner_registry.start(runner=runner)
    return {"status": "started", "mode": "live", "execution_status": "started", "broker": "bybit",
            "trading_account_id": account.id, "account_id": context.account_id,
            "runner_session_id": runner_id, "sessions": [], "force": False, "legacy_account": False}


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

    if request.trading_account_id is not None:
        try:
            web_runner_registry.ensure_instruments_available(
                request.trading_account_id,
                [instrument.ticker for instrument in request.instruments],
            )
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        try:
            selected_account = trading_account_service.get(request.trading_account_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Trading account not found") from error
        if selected_account.broker == BrokerType.BYBIT:
            if not request.instruments:
                raise HTTPException(status_code=400, detail="No instruments selected")
            _ensure_commission_allows_start()
            try:
                return _start_bybit(request, selected_account)
            except ValueError as error:
                raise HTTPException(status_code=400, detail=str(error)) from error

    guard = (
        TradingModeGuard(
            settings=settings,
        )
    )

    try:
        if request.trading_account_id is None:
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

    _ensure_commission_allows_start()

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
                push_notifier
            ),

            commission_service=(
                commission_service
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

            if esm_account.broker == BrokerType.BYBIT:
                return _start_bybit(request, esm_account)

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

            factory.broker = (
                esm_account
                .broker
                .value
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

                commission_service=(
                    commission_service
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


def _account_cash_currency(
    account,
):
    if (
        account
        is None
    ):
        return "RUB"

    if (
        account.broker
        != BrokerType.BYBIT
    ):
        return "RUB"

    return (
        account.base_currency
        or BYBIT_DEFAULT_BASE_CURRENCY
    )


def _parse_snapshot_timestamp(
    value: str | None,
) -> (
    datetime | None
):
    if value is None:
        return None

    try:
        parsed = (
            datetime
            .fromisoformat(
                value,
            )
        )

    except (
        TypeError,
        ValueError,
    ):
        return None

    if (
        parsed.tzinfo
        is None
    ):
        return (
            parsed
            .replace(
                tzinfo=(
                    timezone.utc
                ),
            )
        )

    return (
        parsed
        .astimezone(
            timezone.utc,
        )
    )


# ============================================================
# BALANCE SNAPSHOTS v1.4
# ============================================================

BALANCE_SNAPSHOT_INTERVAL_SECONDS = 15 * 60

BALANCE_SNAPSHOT_RETENTION_DAYS = 180


def _broker_cash_flows_sync(
    account,

    adapter,

    credentials,

    currency: str,
) -> None:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=BALANCE_SNAPSHOT_RETENTION_DAYS)
    sync_state = broker_cash_flow_repository.sync_state(account.id)
    since = cutoff
    if sync_state is not None:
        covered_since = _parse_snapshot_timestamp(sync_state[0])
        synced_at = _parse_snapshot_timestamp(sync_state[1])
        if covered_since is not None and synced_at is not None:
            if now - synced_at < timedelta(minutes=15):
                return
            if covered_since <= cutoff:
                since = max(cutoff, synced_at - timedelta(hours=1))

    operations = (
        adapter
        .get_operations(
            credentials=(
                credentials
            ),

            broker_account_id=(
                account
                .broker_account_id
            ),

            mode=(
                account
                .mode
            ),

            since=since,

            currency=None,
        )
    )

    for operation in operations:
        broker_cash_flow_repository.record_operation(account.id, operation)
        if (
            operation
            .kind
            not in EXTERNAL_FLOW_KINDS
        ):
            continue

        broker_cash_flow_repository\
        .record(
            flow=(
                BrokerCashFlow(
                    trading_account_id=(
                        account.id
                    ),

                    occurred_at=(
                        operation
                        .occurred_at
                        .isoformat()
                    ),

                    kind=(
                        operation
                        .kind
                    ),

                    currency=(
                        operation
                        .currency
                        or currency
                    ),

                    payment=(
                        operation
                        .payment
                    ),
                )
            ),
        )

    broker_cash_flow_repository.mark_synced(
        account.id, cutoff.isoformat(), now.isoformat(),
    )


def _balance_snapshot_once() -> None:
    now = (
        datetime
        .now(
            timezone.utc,
        )
    )

    for account in (
        trading_account_service
        .get_all()
    ):
        if (
            not account.enabled
            or account.mode
            != TradingAccountMode.LIVE
        ):
            continue

        try:
            adapter = (
                broker_registry
                .get(
                    account
                    .broker
                )
            )

            credentials = (
                trading_account_service
                .get_credentials(
                    account.id
                )
            )

            portfolio = (
                adapter
                .get_portfolio(
                    credentials=(
                        credentials
                    ),

                    broker_account_id=(
                        account
                        .broker_account_id
                    ),

                    mode=(
                        account
                        .mode
                    ),
                )
            )

            balance_snapshot_repository\
                .record(
                    snapshot=(
                        BalanceSnapshot(
                            created_at=(
                                now
                                .isoformat()
                            ),

                            trading_account_id=(
                                account.id
                            ),

                            currency=(
                                _account_cash_currency(
                                    account
                                )
                            ),

                            equity=(
                                portfolio
                                .total_value
                                if (
                                    portfolio
                                    .total_value
                                    is not None
                                )
                                else (
                                    portfolio
                                    .cash
                                )
                            ),
                        )
                    ),
                )

            try:
                _broker_cash_flows_sync(
                    account=(
                        account
                    ),

                    adapter=(
                        adapter
                    ),

                    credentials=(
                        credentials
                    ),

                    currency=(
                        _account_cash_currency(
                            account
                        )
                    ),
                )

            except Exception as error:
                print(
                    "BROKER CASH FLOWS SYNC ERROR:",
                    account.id,
                    repr(
                        error
                    ),
                )

        except Exception as error:
            print(
                "BALANCE SNAPSHOT ERROR:",
                account.id,
                repr(
                    error,
                ),
            )


def _balance_snapshot_worker() -> None:
    while True:
        try:
            _balance_snapshot_once()

            cutoff = (
                datetime
                .now(
                    timezone.utc,
                )
                - timedelta(
                    days=(
                        BALANCE_SNAPSHOT_RETENTION_DAYS
                    ),
                )
            )

            balance_snapshot_repository\
                .delete_older_than(
                    cutoff=(
                        cutoff
                        .isoformat()
                    ),
                )

        except Exception as error:
            print(
                "BALANCE SNAPSHOT WORKER ERROR:",
                repr(
                    error,
                ),
            )

        time.sleep(
            BALANCE_SNAPSHOT_INTERVAL_SECONDS
        )


threading.Thread(
    target=(
        _balance_snapshot_worker
    ),

    daemon=(
        True
    ),

    name=(
        "balance-snapshot-worker"
    ),
).start()


def _balance_backfill_account(
    account,
) -> None:
    try:
        adapter = (
            broker_registry
            .get(
                account
                .broker
            )
        )

        credentials = (
            trading_account_service
            .get_credentials(
                account.id
            )
        )

        done = (
            balance_backfill_service
            .backfill_account(
                account=(
                    account
                ),

                adapter=(
                    adapter
                ),

                credentials=(
                    credentials
                ),

                currency=(
                    _account_cash_currency(
                        account
                    )
                ),
            )
        )

        if done:
            print(
                "BALANCE BACKFILL DONE:",
                account.id,
            )

    except Exception as error:
        print(
            "BALANCE BACKFILL ERROR:",
            account.id,
            repr(
                error
            ),
        )


def _balance_backfill_startup() -> None:
    for account in (
        trading_account_service
        .get_all()
    ):
        if (
            not account.enabled
            or account.mode
            != TradingAccountMode.LIVE
        ):
            continue

        _balance_backfill_account(
            account
        )


threading.Thread(
    target=(
        _balance_backfill_startup
    ),

    daemon=(
        True
    ),

    name=(
        "balance-backfill-worker"
    ),
).start()


# ============================================================
# DASHBOARD
# ============================================================

def _usd_rub_rate() -> Decimal | None:
    try:
        token = instrument_catalog_service._resolve_token(None)
        with TInvestClientFactory(token=token).create_client() as client:
            instruments = client.instruments.currencies().instruments
            instrument = next((item for item in instruments if item.ticker == "USD000UTSTOM"), None)
            if instrument is None:
                return None
            response = client.market_data.get_last_prices(instrument_id=[instrument.uid])
        if not response.last_prices:
            return None
        raw = response.last_prices[0].price
        rate = Decimal(raw.units) + Decimal(raw.nano) / Decimal("1000000000")
        return rate if rate.is_finite() and rate > 0 else None
    except Exception:
        return None


def _dashboard_total_balance(accounts: list[dict]) -> dict:
    enabled = [account for account in accounts if account.get("enabled", True)]
    currencies = {account["currency"] for account in enabled}
    platforms = {account["broker"] for account in enabled}
    target = next(iter(currencies)) if len(platforms) <= 1 and len(currencies) == 1 else "RUB"
    rates = {"RUB": Decimal("1")}
    needs_dollar = target == "RUB" and bool(currencies & {"USD", "USDT", "USDC"})
    rate = _usd_rub_rate() if needs_dollar else None
    if rate is not None:
        rates.update({currency: rate for currency in ("USD", "USDT", "USDC")})
    missing = [account for account in enabled if account.get("balance") is None or (target == "RUB" and account["currency"] not in rates)]
    total = None if missing else sum((
        Decimal(str(account["balance"])) * (rates[account["currency"]] if target == "RUB" else Decimal("1"))
        for account in enabled
    ), Decimal("0"))
    return {"total_balance": float(total) if total is not None else None, "total_balance_currency": target,
            "balance_conversion_note": "Нет актуального курса Т-Инвест или баланса одного из счетов" if missing else None,
            "exchange_rates_rub": {currency: float(value) for currency, value in rates.items()}}


@app.get("/api/dashboard")
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

    invested_cash_by_currency: dict[
        str,
        Decimal,
    ] = {}

    invested_cash_by_account: dict[
        str,
        Decimal,
    ] = {}

    account_by_id = {
        account.id: account
        for account
        in configured_accounts
    }

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

        runner_account_id = (
            getattr(runner, "trading_account_id", None)
            or getattr(runner.context, "trading_account_id", None)
        )

        runner_currency = (
            _account_cash_currency(
                account_by_id.get(
                    runner_account_id,
                )
            )
        )

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
                position_value = (
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

                invested_cash += position_value

                invested_cash_by_currency[
                    runner_currency
                ] = (
                    invested_cash_by_currency.get(
                        runner_currency,
                        Decimal("0"),
                    )
                    + position_value
                )

                if (
                    runner_account_id
                    is not None
                ):
                    invested_cash_by_account[
                        runner_account_id
                    ] = (
                        invested_cash_by_account.get(
                            runner_account_id,
                            Decimal("0"),
                        )
                        + position_value
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
            state_currency = (
                _account_cash_currency(
                    account_by_id.get(
                        state.trading_account_id
                    )
                )
            )

            for instrument in state.instruments:
                for position in instrument.open_positions:
                    purchase_cost = getattr(
                        position,
                        "purchase_cost",
                        None,
                    )

                    if purchase_cost is not None:
                        purchase_value = Decimal(
                            str(purchase_cost)
                        )

                        invested_cash += purchase_value

                        invested_cash_by_currency[
                            state_currency
                        ] = (
                            invested_cash_by_currency.get(
                                state_currency,
                                Decimal("0"),
                            )
                            + purchase_value
                        )

                        if (
                            state
                            .trading_account_id
                            is not None
                        ):
                            invested_cash_by_account[
                                state
                                .trading_account_id
                            ] = (
                                invested_cash_by_account.get(
                                    state
                                    .trading_account_id,

                                    Decimal(
                                        "0",
                                    ),
                                )
                                + purchase_value
                            )

    # Real free broker cash: each enabled LIVE account exactly once.
    live_cash = Decimal("0")
    live_cash_accounts = 0
    cash_by_currency: dict[
        str,
        Decimal,
    ] = {}

    cash_by_account: dict[
        str,
        Decimal,
    ] = {}

    broker_equity_by_account: dict[str, Decimal] = {}

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

            account_currency = (
                _account_cash_currency(
                    account
                )
            )

            live_cash += portfolio.cash
            cash_by_currency[account_currency] = (
                cash_by_currency.get(
                    account_currency,
                    Decimal("0"),
                )
                + portfolio.cash
            )
            cash_by_account[account.id] = (
                cash_by_account.get(
                    account.id,
                    Decimal("0"),
                )
                + portfolio.cash
            )
            broker_equity_by_account[account.id] = (
                portfolio.total_value
                if portfolio.total_value is not None
                else portfolio.cash + invested_cash_by_account.get(
                    account.id,
                    Decimal("0"),
                )
            )
            live_cash_accounts += 1
            balance_snapshot_repository.record_if_due(BalanceSnapshot(
                created_at=datetime.now(timezone.utc).isoformat(),
                trading_account_id=account.id,
                currency=account_currency,
                equity=broker_equity_by_account[account.id],
            ))

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
        cash_by_currency["RUB"] = (
            cash_by_currency.get(
                "RUB",
                Decimal("0"),
            )
            + live_cash
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

    now = (
        datetime
        .now(
            timezone.utc,
        )
    )

    latest_snapshot_by_account = {}

    snapshots_by_account_for_pnl = {}

    try:
        for snapshot in (
            balance_snapshot_repository
            .get_since(
                since=(
                    now
                    - timedelta(
                        days=190,
                    )
                )
                .isoformat(),
            )
        ):
            latest_snapshot_by_account[
                snapshot
                .trading_account_id
            ] = (
                snapshot
                .equity
            )

            snapshot_ts = (
                _parse_snapshot_timestamp(
                    snapshot
                    .created_at,
                )
            )

            if (
                snapshot_ts
                is not None
            ):
                snapshots_by_account_for_pnl\
                    .setdefault(
                        snapshot
                        .trading_account_id,

                        [],
                    )\
                    .append(
                        (
                            snapshot_ts,

                            snapshot
                            .equity,
                        )
                    )

    except Exception as error:
        print(
            "DASHBOARD ACCOUNT SNAPSHOTS ERROR:",
            repr(
                error,
            ),
        )

    account_equity_by_id = {}

    for account in (
        configured_accounts
    ):
        snapshot_equity = (
            latest_snapshot_by_account
            .get(
                account.id,
            )
        )

        if account.id in broker_equity_by_account:
            account_equity_by_id[account.id] = (
                broker_equity_by_account[account.id]
            )

        elif (
            snapshot_equity
            is not None
        ):
            account_equity_by_id[
                account.id
            ] = (
                snapshot_equity
            )

        elif (
            account.id
            in cash_by_account
        ):
            account_equity_by_id[
                account.id
            ] = (
                cash_by_account[
                    account.id
                ]
                + invested_cash_by_account.get(
                    account.id,
                    Decimal(
                        "0",
                    ),
                )
            )

    try:
        pnl_today_by_account = (
            equity_history_service
            .pnl_today_by_account(
                current_equity_by_account=(
                    account_equity_by_id
                    or None
                ),

                snapshots_by_account=(
                    snapshots_by_account_for_pnl
                    or None
                ),
            )
        )

    except Exception as error:
        print(
            "DASHBOARD PNL BY ACCOUNT ERROR:",
            repr(
                error,
            ),
        )

        pnl_today_by_account = {}

    accounts_detail = []

    for account in configured_accounts:
        snapshot_equity = (
            latest_snapshot_by_account
            .get(
                account.id,
            )
        )

        if account.id in broker_equity_by_account:
            account_balance = float(broker_equity_by_account[account.id])

        elif (
            snapshot_equity
            is not None
        ):
            account_balance = (
                float(
                    snapshot_equity,
                )
            )

        elif (
            account.id
            in cash_by_account
        ):
            account_balance = (
                float(
                    cash_by_account[
                        account.id
                    ]
                    + invested_cash_by_account.get(
                        account.id,
                        Decimal(
                            "0",
                        ),
                    )
                )
            )

        else:
            account_balance = None

        account_pnl_today = (
            pnl_today_by_account
            .get(
                account.id,
            )
        )

        accounts_detail.append(
            {
                "id": (
                    account.id
                ),

                "name": (
                    account.name
                ),

                "broker": (
                    account
                    .broker
                    .value
                ),

                "mode": (
                    account
                    .mode
                    .value
                ),

                "enabled": (
                    account.enabled
                ),

                "currency": (
                    _account_cash_currency(
                        account,
                    )
                ),

                "balance": (
                    account_balance
                ),

                "pnl_today": (
                    float(
                        account_pnl_today,
                    )

                    if (
                        account_pnl_today
                        is not None
                    )

                    else None
                ),
            }
        )

    totals = _dashboard_total_balance(accounts_detail)
    return {
        **totals,
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

        "total_equity": (
            float(
                sum(
                    account_equity_by_id
                    .values()
                )
            )

            if account_equity_by_id

            else None
        ),

        "invested_cash":
            float(invested_cash),

        "invested_cash_by_currency": {
            currency: float(
                amount
            )
            for currency, amount
            in sorted(
                invested_cash_by_currency.items()
            )
        },

        "available_cash": (
            float(
                cash_by_currency.get(
                    "RUB",
                    live_cash,
                )
            )
            if (
                live_cash_accounts > 0
                or active_states
            )
            else None
        ),

        "available_cash_by_currency": {
            currency: float(
                amount
            )
            for currency, amount
            in sorted(
                cash_by_currency.items()
            )
        },

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

        "accounts_detail":
            accounts_detail,
    }


@app.get(
    "/api/dashboard/history"
)
def dashboard_history(
    days: int = 7,
):
    if days not in (7, 30, 90, 180):
        days = 7

    summary = dashboard()

    total_equity = (
        summary
        .get(
            "total_equity",
        )
    )

    available = (
        summary
        .get(
            "available_cash",
        )
    )

    now = (
        datetime
        .now(
            timezone.utc,
        )
    )

    if (
        total_equity
        is None
        and available
        is None
    ):
        return {
            "days":
                days,

            "equity":
                None,

            "points":
                [],

            "pnl_today":
                None,

            "pnl_today_percent":
                None,

            "updated_at": (
                now
                .isoformat()
            ),
        }

    if total_equity is None:
        invested = Decimal(
            str(
                summary
                .get(
                    "invested_cash",
                )
                or 0,
            )
        )

        total_equity = float(
            invested
            + Decimal(
                str(
                    available,
                )
            )
        )

    current_equity = (
        Decimal(
            str(
                total_equity,
            )
        )
    )

    available_by_currency = (
        summary
        .get(
            "available_cash_by_currency",
        )
        or {}
    )

    invested_by_currency = (
        summary
        .get(
            "invested_cash_by_currency",
        )
        or {}
    )

    current_equity_by_currency: dict[str, Decimal] = {}
    current_equity_by_account: dict[str, Decimal] = {}

    for account in summary.get("accounts_detail", []):
        if account.get("balance") is None:
            continue
        equity = Decimal(str(account["balance"]))
        currency = account["currency"]
        current_equity_by_account[account["id"]] = equity
        current_equity_by_currency[currency] = (
            current_equity_by_currency.get(currency, Decimal("0"))
            + equity
        )

    for currency in (
        sorted(
            set(
                available_by_currency
            )
            | set(
                invested_by_currency
            )
        )
    ):
        if currency in current_equity_by_currency:
            continue
        current_equity_by_currency[
            currency
        ] = (
            Decimal(
                str(
                    available_by_currency
                    .get(
                        currency,
                        0,
                    )
                )
            )
            + Decimal(
                str(
                    invested_by_currency
                    .get(
                        currency,
                        0,
                    )
                )
            )
        )

    since = (
        now
        - timedelta(
            days=days,
        )
    )

    snapshots_by_currency: dict[str, list[tuple[datetime, Decimal]]] = {}

    snapshots_by_account: dict[str, list[tuple[datetime, Decimal]]] = {}

    try:
        latest_by_slot = {}

        latest_by_account_slot = {}

        for snapshot in (
            balance_snapshot_repository
            .get_since(
                since=(
                    since
                    .isoformat()
                ),
            )
        ):
            ts = (
                _parse_snapshot_timestamp(
                    snapshot
                    .created_at,
                )
            )

            if (
                ts
                is None
            ):
                continue

            tick = (
                ts
                .replace(
                    minute=(
                        (
                            ts.minute
                            // 15
                        )
                        * 15
                    ),

                    second=0,

                    microsecond=0,
                )
            )

            latest_by_slot[
                (
                    snapshot
                    .currency,
                    tick,
                    snapshot
                    .trading_account_id,
                )
            ] = (
                ts,
                snapshot
                .equity,
            )

            latest_by_account_slot[
                (
                    snapshot
                    .trading_account_id,
                    tick,
                )
            ] = (
                ts,
                snapshot
                .equity,
            )

        totals: dict[tuple[str, datetime], Decimal] = {}

        last_ts: dict[tuple[str, datetime], datetime] = {}

        for (
            currency,
            tick,
            _account_id,
        ), (
            ts,
            equity,
        ) in (
            latest_by_slot
            .items()
        ):
            slot = (
                currency,
                tick,
            )

            totals[
                slot
            ] = (
                totals.get(
                    slot,
                    Decimal(
                        "0",
                    ),
                )
                + equity
            )

            previous = (
                last_ts
                .get(
                    slot,
                )
            )

            if (
                previous
                is None
                or ts
                > previous
            ):
                last_ts[
                    slot
                ] = ts

        for (
            currency,
            tick,
        ), total in (
            totals
            .items()
        ):
            snapshots_by_currency\
                .setdefault(
                    currency,
                    [],
                )\
                .append(
                    (
                        last_ts[
                            (
                                currency,
                                tick,
                            )
                        ],
                        total,
                    )
                )

        for (
            account_id,
            _tick,
        ), (
            ts,
            equity,
        ) in (
            latest_by_account_slot
            .items()
        ):
            snapshots_by_account\
                .setdefault(
                    account_id,
                    [],
                )\
                .append(
                    (
                        ts,
                        equity,
                    )
                )

    except Exception as error:
        print(
            "DASHBOARD HISTORY SNAPSHOTS ERROR:",
            repr(
                error,
            ),
        )

        snapshots_by_currency = {}

        snapshots_by_account = {}

    history_accounts = (
        trading_account_service
        .get_all()
    )

    account_currency_by_id = {
        account.id: (
            _account_cash_currency(
                account
            )
        )

        for account
        in history_accounts
    }

    account_name_by_id = {
        account.id: (
            account
            .name
        )

        for account
        in history_accounts
    }

    for account in summary.get("accounts_detail", []):
        account_currency_by_id.setdefault(account["id"], account["currency"])
        account_name_by_id.setdefault(account["id"], account.get("name") or account["id"])

    first_snapshot_by_currency: dict[str, tuple[datetime, Decimal]] | None = None

    try:
        first_snapshots = (
            balance_snapshot_repository
            .get_first_by_currency()
        )

        if first_snapshots:
            first_snapshot_by_currency = {}

            for (
                currency,

                snapshot,
            ) in (
                first_snapshots
                .items()
            ):
                snapshot_ts = (
                    _parse_snapshot_timestamp(
                        snapshot
                        .created_at
                    )
                )

                if (
                    snapshot_ts
                    is None
                ):
                    continue

                first_snapshot_by_currency[
                    currency
                ] = (
                    snapshot_ts,

                    snapshot
                    .equity,
                )

    except Exception as error:
        print(
            "DASHBOARD HISTORY FIRST SNAPSHOT ERROR:",
            repr(
                error
            ),
        )

        first_snapshot_by_currency = (
            None
        )

    history_response = (
        equity_history_service
        .build(
            current_equity=(
                current_equity
            ),

            days=days,

            current_equity_by_currency=(
                current_equity_by_currency
                or None
            ),

            account_currency_by_id=(
                account_currency_by_id
            ),

            snapshots_by_currency=(
                snapshots_by_currency
                or None
            ),

            first_snapshot_by_currency=(
                first_snapshot_by_currency
            ),
        )
    )

    points_by_account = {}

    for account_id, account_snapshots in (
        snapshots_by_account
        .items()
    ):
        account_snapshots.sort(
            key=(
                lambda item: (
                    item[
                        0
                    ]
                )
            ),
        )

        points_by_account[
            account_id
        ] = (
            equity_history_service
            .snapshot_points(
                snapshots=(
                    account_snapshots
                ),

                now=now,
                current_equity=current_equity_by_account.get(account_id),
            )
        )

    for account_id, equity in current_equity_by_account.items():
        points_by_account.setdefault(account_id, [{"ts": now.isoformat(), "equity": float(equity)}])

    actual_points_by_currency = {
        currency: equity_history_service.snapshot_points(
            snapshots=sorted(snapshots, key=lambda item: item[0]),
            now=now,
            current_equity=current_equity_by_currency.get(currency),
        )
        for currency, snapshots in snapshots_by_currency.items()
    }
    for currency, equity in current_equity_by_currency.items():
        actual_points_by_currency.setdefault(currency, [{"ts": now.isoformat(), "equity": float(equity)}])
    history_response["points_by_currency"] = actual_points_by_currency
    history_response["points"] = (
        next(iter(actual_points_by_currency.values()))
        if len(actual_points_by_currency) == 1 else []
    )
    history_response["history_note"] = (
        "История стоимости портфеля показана только по сохранённым снимкам. "
        "Операции платформы не заменяют историческую стоимость активов."
    )

    rates = summary.get("exchange_rates_rub", {})
    total_currency = summary.get("total_balance_currency", "RUB")
    account_ids = list(current_equity_by_account)
    factors = {
        account_id: (rates.get(account_currency_by_id.get(account_id, "RUB")) if total_currency == "RUB" else 1)
        for account_id in account_ids
    }
    total_points = []
    if account_ids and all(factors[account_id] is not None for account_id in account_ids):
        by_time: dict[str, dict[str, float]] = {}
        for account_id in account_ids:
            for point in points_by_account.get(account_id, []):
                by_time.setdefault(point["ts"], {})[account_id] = point["equity"]
        latest = {}
        for timestamp, values in sorted(by_time.items()):
            latest.update(values)
            if all(account_id in latest for account_id in account_ids):
                total_points.append({"ts": timestamp, "equity": sum(latest[account_id] * factors[account_id] for account_id in account_ids)})
    history_response["total_points"] = total_points
    history_response["total_balance_currency"] = total_currency
    history_response["exchange_rates_rub"] = rates
    history_response["accounts"] = [
        {"id": account["id"], "name": account.get("name") or account["id"], "currency": account["currency"], "broker": account.get("broker")}
        for account in summary.get("accounts_detail", [])
    ]
    if len(current_equity_by_currency) > 1:
        history_response["history_note"] += " Общая линия пересчитана по текущему курсу Т-Инвест, не по историческим валютным курсам."

    if points_by_account:
        history_response[
            "points_by_account"
        ] = (
            points_by_account
        )

        history_response[
            "accounts"
        ] = [
            {
                "id": (
                    account_id
                ),

                "name": (
                    account_name_by_id
                    .get(
                        account_id,
                        account_id,
                    )
                ),

                "currency": (
                    account_currency_by_id
                    .get(
                        account_id,
                        "RUB",
                    )
                ),
                "broker": next((account.get("broker") for account in summary.get("accounts_detail", []) if account["id"] == account_id), None),
            }

            for account_id
            in sorted(
                points_by_account,
            )
        ]

    return history_response

# ============================================================
# ACCOUNTS OVERVIEW 1.4 (пп. 3 и 6 плана)
# ============================================================

OVERVIEW_PLANNED_LEVEL_STATUSES = {
    "WAITING_PRICE",
    "WAITING_FOR_FUNDS",
    "TRAILING_ENTRY",
}


def _overview_change_24h(
    token: str | None,
    instrument_uid: str | None,
) -> (
    tuple[
        float,
        float,
    ]
    | None
):
    if (
        not token
        or not instrument_uid
    ):
        return None

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
                    instrument_uid
                ),

                date_from=(
                    now
                    - timedelta(
                        days=10,
                    )
                ),

                date_to=(
                    now
                ),
            )
        )

    except Exception as error:
        print(
            "OVERVIEW CHANGE 24H FAILED:",
            instrument_uid,
            repr(
                error
            ),
        )

        return None

    if (
        len(
            candles
        )
        < 2
    ):
        return None

    last_close = (
        candles[
            -1
        ]
        .close
    )

    previous_close = (
        candles[
            -2
        ]
        .close
    )

    if (
        previous_close
        == 0
    ):
        return None

    change = (
        last_close
        - previous_close
    )

    change_percent = (
        change
        / previous_close
        * Decimal(
            "100"
        )
    )

    return (
        float(
            change
        ),

        float(
            change_percent
        ),
    )


@app.get(
    "/api/overview"
)
def accounts_overview():
    now = (
        datetime
        .now(
            timezone.utc,
        )
    )

    configured_accounts = (
        trading_account_service
        .get_all()
    )

    sessions_by_ticker = {}

    for web_session in (
        session_registry
        .get_sessions()
    ):
        display = (
            _build_display_session(
                web_session=(
                    web_session
                ),
            )
        )

        sessions_by_ticker[
            display[
                "ticker"
            ]
            .upper()
        ] = display

    instruments_by_account = {}

    states_by_account = {}

    seen_instruments: set[tuple[str, str]] = set()

    for state in (
        trading_state_repository
        .get_all()
    ):
        if state.status.upper() not in {"RUNNING", "DRAINING", "RECOVERY", "ACTIVE"}:
            continue
        account_key = (
            state
            .trading_account_id
            or ""
        )

        if (
            not account_key
        ):
            continue

        if any(
            (account_key, instrument.instrument_uid) in seen_instruments
            for instrument in state.instruments
        ):
            continue

        states_by_account\
        .setdefault(
            account_key,
            [],
        )\
        .append(
            state
        )

        for instrument in (
            state
            .instruments
        ):
            ticker_key = (
                instrument
                .ticker
                .upper()
            )

            instrument_key = (account_key, instrument.instrument_uid)
            if instrument_key in seen_instruments:
                continue
            seen_instruments.add(instrument_key)

            instruments_by_account\
            .setdefault(
                account_key,
                {},
            )\
            .setdefault(
                ticker_key,
                [],
            )\
            .append(
                instrument
            )

    invested_by_account = {}

    reserved_by_account = {}

    for runner in (
        web_runner_registry
        .get_all()
    ):
        runner_account_id = (
            getattr(runner, "trading_account_id", None)
            or getattr(runner.context, "trading_account_id", None)
            or ""
        )

        for trading_session in (
            runner
            .context
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
                position_value = (
                    Decimal(
                        str(
                            position
                            .entry_price,
                        )
                    )
                    * Decimal(
                        str(
                            position
                            .quantity,
                        )
                    )
                    + Decimal(
                        str(
                            getattr(
                                position,
                                "buy_commission",
                                Decimal(
                                    "0"
                                ),
                            )
                            or Decimal(
                                "0"
                            )
                        )
                    )
                )

                invested_by_account[
                    runner_account_id
                ] = (
                    invested_by_account
                    .get(
                        runner_account_id,

                        Decimal(
                            "0"
                        ),
                    )
                    + position_value
                )

        reservation_manager = (
            runner
            .context
            .trade_capital_service
            .reservation_manager
        )

        reserved_by_account[
            runner_account_id
        ] = (
            reserved_by_account
            .get(
                runner_account_id,

                Decimal(
                    "0"
                ),
            )
            + reservation_manager
            .get_reserved_total()
        )

    runner_account_ids = {
        getattr(runner, "trading_account_id", None)
        or getattr(runner.context, "trading_account_id", "")
        for runner in web_runner_registry.get_all()
    }

    if states_by_account:
        for account_key, account_states in (
            states_by_account
            .items()
        ):
            if account_key in runner_account_ids:
                continue
            for state in (
                account_states
            ):
                reserved_by_account[
                    account_key
                ] = (
                    reserved_by_account
                    .get(
                        account_key,

                        Decimal(
                            "0"
                        ),
                    )
                    + (
                        state
                        .reserved_cash
                        or Decimal(
                            "0"
                        )
                    )
                )

                for instrument in (
                    state
                    .instruments
                ):
                    for position in (
                        instrument
                        .open_positions
                    ):
                        purchase_cost = (
                            getattr(
                                position,
                                "purchase_cost",
                                None,
                            )
                        )

                        if (
                            purchase_cost
                            is not None
                        ):
                            invested_by_account[
                                account_key
                            ] = (
                                invested_by_account
                                .get(
                                    account_key,

                                    Decimal(
                                        "0"
                                    ),
                                )
                                + Decimal(
                                    str(
                                        purchase_cost
                                    )
                                )
                            )

    cash_by_account = {}
    broker_equity_by_account = {}

    for account in (
        configured_accounts
    ):
        if (
            not account
            .enabled
        ):
            continue

        try:
            adapter = (
                broker_registry
                .get(
                    account
                    .broker
                )
            )

            credentials = (
                trading_account_service
                .get_credentials(
                    account
                    .id
                )
            )

            portfolio = (
                adapter
                .get_portfolio(
                    credentials=(
                        credentials
                    ),

                    broker_account_id=(
                        account
                        .broker_account_id
                    ),

                    mode=(
                        account
                        .mode
                    ),
                )
            )

            cash_by_account[
                account
                .id
            ] = (
                portfolio
                .cash
            )
            if portfolio.total_value is not None:
                broker_equity_by_account[account.id] = portfolio.total_value

        except Exception as error:
            print(
                "OVERVIEW PORTFOLIO ERROR:",
                account
                .id,
                repr(
                    error
                ),
            )

    series_by_account = {}

    latest_equity_by_account = {}

    try:
        snapshots_by_account = {}

        for snapshot in (
            balance_snapshot_repository
            .get_since(
                since=(
                    now
                    - timedelta(
                        days=190,
                    )
                )
                .isoformat(),
            )
        ):
            ts = (
                _parse_snapshot_timestamp(
                    snapshot
                    .created_at,
                )
            )

            if (
                ts
                is None
            ):
                continue

            snapshots_by_account\
            .setdefault(
                snapshot
                .trading_account_id,
                [],
            )\
            .append(
                (
                    ts,
                    snapshot
                    .equity,
                )
            )

        for account_id, account_snapshots in (
            snapshots_by_account
            .items()
        ):
            account_snapshots\
            .sort(
                key=(
                    lambda item: (
                        item[
                            0
                        ]
                    )
                ),
            )

            latest_equity_by_account[
                account_id
            ] = (
                account_snapshots[
                    -1
                ][
                    1
                ]
            )

            recent = [
                item
                for item
                in account_snapshots

                if (
                    item[
                        0
                    ]
                    >= (
                        now
                        - timedelta(
                            days=7,
                        )
                    )
                )
            ]

            if (
                recent
            ):
                series_by_account[
                    account_id
                ] = (
                    equity_history_service
                    .snapshot_points(
                        snapshots=(
                            recent
                        ),

                        now=(
                            now
                        ),
                    )
                )

    except Exception as error:
        print(
            "OVERVIEW SNAPSHOTS ERROR:",
            repr(
                error
            ),
        )

    change_cache = {}

    accounts_response = []

    for account in (
        configured_accounts
    ):
        account_states = (
            states_by_account
            .get(
                account
                .id,

                [],
            )
        )

        currency = (
            _account_cash_currency(
                account
            )
        )

        invested = (
            invested_by_account
            .get(
                account
                .id,

                Decimal(
                    "0"
                ),
            )
        )

        available = (
            cash_by_account
            .get(
                account
                .id,
            )
        )

        if (
            available
            is None
            and account_states
        ):
            available = (
                account_states[
                    0
                ]
                .available_cash
            )

        snapshot_equity = (
            latest_equity_by_account
            .get(
                account
                .id,
            )
        )

        if account.id in broker_equity_by_account:
            equity = broker_equity_by_account[account.id]

        elif (
            snapshot_equity
            is not None
        ):
            equity = (
                snapshot_equity
            )

        elif (
            available
            is not None
        ):
            equity = (
                Decimal(
                    str(
                        available
                    )
                )
                + invested
            )

        else:
            equity = None

        reserved = (
            reserved_by_account
            .get(
                account
                .id,
            )
        )

        assets = [
            {
                "ticker": (
                    currency
                ),

                "kind": (
                    "currency"
                ),

                "quantity": (
                    float(
                        available
                    )

                    if (
                        available
                        is not None
                    )

                    else None
                ),

                "quantity_precision": 2,

                "price": 1.0,

                "value": (
                    float(
                        available
                    )

                    if (
                        available
                        is not None
                    )

                    else None
                ),

                "change_24h": (
                    None
                ),

                "change_24h_percent": (
                    None
                ),
            }
        ]

        account_sessions = []

        account_token = (
            _resolve_chart_token(
                account_states[
                    -1
                ]
            )

            if account_states

            else None
        )

        account_instruments = (
            instruments_by_account
            .get(
                account
                .id,
            )
            or {}
        )

        for ticker, instrument_states in (
            account_instruments
            .items()
        ):
            display = (
                sessions_by_ticker
                .get(
                    ticker,
                )
            )

            quantity = sum(
                (
                    Decimal(
                        str(
                            position
                            .quantity,
                        )
                    )

                    for instrument in (
                        instrument_states
                    )

                    for position in (
                        instrument
                        .open_positions
                    )
                ),

                Decimal(
                    "0"
                ),
            )

            entry_value = sum(
                (
                    position.purchase_cost - getattr(position, "buy_commission", Decimal("0"))
                    if position.purchase_cost is not None
                    else position.entry_price * Decimal(str(position.quantity))

                    for instrument in (
                        instrument_states
                    )

                    for position in (
                        instrument
                        .open_positions
                    )
                ),

                Decimal(
                    "0"
                ),
            )

            price = (
                display.get("current_price")
                if display is not None
                else (
                    float(instrument_states[0].current_price)
                    if instrument_states[0].current_price is not None else None
                )
            )

            if (
                price
                is not None
            ):
                effective_units = sum(
                    (
                        (position.purchase_cost - getattr(position, "buy_commission", Decimal("0")))
                        / position.entry_price
                        if position.purchase_cost is not None and position.entry_price > 0
                        else Decimal(str(position.quantity))
                        for instrument in instrument_states
                        for position in instrument.open_positions
                    ),
                    Decimal("0"),
                )
                value = effective_units * Decimal(str(price))

            elif (
                entry_value
                > 0
            ):
                value = (
                    entry_value
                )

            else:
                value = None

            instrument_uid = (
                instrument_states[
                    0
                ]
                .instrument_uid
            )

            change_key = (
                account_token,

                instrument_uid,
            )

            if (
                change_key
                not in change_cache
            ):
                change_cache[
                    change_key
                ] = (
                    _overview_change_24h(
                        token=(
                            account_token
                        ),

                        instrument_uid=(
                            instrument_uid
                        ),
                    )
                )

            change = (
                change_cache[
                    change_key
                ]
            )

            quantity_precision = (
                12

                if (
                    account
                    .broker
                    .value
                    == "bybit"
                )

                else 2
            )

            assets\
            .append(
                {
                    "ticker": (
                        instrument_states[
                            0
                        ]
                        .ticker
                    ),

                    "kind": (
                        "instrument"
                    ),

                    "quantity": (
                        float(
                            quantity
                        )

                        if (
                            quantity
                            > 0
                        )

                        else None
                    ),

                    "quantity_precision": (
                        quantity_precision
                    ),

                    "price": (
                        price
                    ),

                    "value": (
                        float(
                            value
                        )

                        if (
                            value
                            is not None
                        )

                        else None
                    ),

                    "change_24h": (
                        change[
                            0
                        ]

                        if (
                            change
                            is not None
                        )

                        else None
                    ),

                    "change_24h_percent": (
                        change[
                            1
                        ]

                        if (
                            change
                            is not None
                        )

                        else None
                    ),
                }
            )

            orders_bought = []

            orders_planned = []

            for instrument in (
                instrument_states
            ):
                for position in (
                    instrument
                    .open_positions
                ):
                    orders_bought\
                    .append(
                        {
                            "level_index": (
                                position
                                .level_index
                            ),

                            "price": (
                                str(
                                    position
                                    .entry_price
                                )
                            ),

                            "quantity": (
                                float(
                                    position
                                    .quantity
                                )
                            ),

                            "exit_target": (
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
                        }
                    )

                for level in (
                    instrument
                    .levels
                ):
                    if (
                        level
                        .status
                        in (
                            OVERVIEW_PLANNED_LEVEL_STATUSES
                        )
                    ):
                        orders_planned\
                        .append(
                            {
                                "level_index": (
                                    level
                                    .level_index
                                ),

                                "price": (
                                    str(
                                        level
                                        .level_price
                                    )
                                ),

                                "status": (
                                    level
                                    .status
                                ),
                            }
                        )

            closed_orders = sum(item.cycle_closed_orders for item in instrument_states)
            cycle_realized = sum(
                (item.cycle_realized_profit for item in instrument_states),
                Decimal("0"),
            )
            unrealized = (
                Decimal(str(display.get("unrealized_profit", 0)))
                if display is not None else Decimal("0")
            )
            if display is None and price is not None:
                unrealized = sum(
                    (
                        (Decimal(str(price)) - position.entry_price)
                        * (
                            (position.purchase_cost - position.buy_commission) / position.entry_price
                            if position.purchase_cost is not None and position.entry_price > 0
                            else Decimal(position.quantity)
                        )
                        - position.buy_commission
                        for instrument in instrument_states
                        for position in instrument.open_positions
                    ),
                    Decimal("0"),
                )
            cycle_profit = cycle_realized + unrealized
            purchase_cost = sum(
                (
                    position.purchase_cost
                    if position.purchase_cost is not None
                    else position.entry_price * Decimal(position.quantity) + position.buy_commission
                    for instrument in instrument_states
                    for position in instrument.open_positions
                ),
                Decimal("0"),
            )
            pnl_percent = float(cycle_profit / purchase_cost * 100) if purchase_cost > 0 else None
            buy_candidates = []
            sell_candidates = []
            for instrument in instrument_states:
                positions_by_level = {item.level_index: item for item in instrument.open_positions}
                for level in sorted(instrument.levels, key=lambda item: item.level_index):
                    if level.status not in OVERVIEW_PLANNED_LEVEL_STATUSES:
                        continue
                    if not instrument.open_positions and instrument.session_start_price is not None:
                        start_price = instrument.session_start_price
                        buy_candidates.extend([
                            start_price * Decimal("0.995"),
                            start_price * Decimal("1.005"),
                        ])
                        break
                    previous = positions_by_level.get(level.level_index - 1)
                    if previous is not None and instrument.grid_step is not None:
                        buy_candidates.append(previous.entry_price - instrument.grid_step)
                        break
                    if instrument.grid_step is None:
                        buy_candidates.append(level.level_price)
                        break
                config = instrument.grid_config
                multiplier = (
                    (Decimal("1") - config.trailing_percent / 100)
                    * (Decimal("1") - config.exit_limit_offset_percent / 100)
                    if config is not None else Decimal("0.99700225")
                )
                if multiplier > 0:
                    sell_candidates.extend(
                        position.hard_take_profit_price / multiplier
                        for position in instrument.open_positions
                    )

            account_sessions\
            .append(
                {
                    "closed_orders": closed_orders if orders_bought else 0,
                    "cycle_profit": float(cycle_profit) if orders_bought else 0.0,
                    "pnl_percent": pnl_percent,
                    "next_buy_activation": float(min(
                        buy_candidates,
                        key=lambda target: abs(target - Decimal(str(price))) if price is not None else -target,
                    )) if buy_candidates else None,
                    "next_sell_activation": float(min(sell_candidates)) if sell_candidates else None,
                    "ticker": (
                        instrument_states[
                            0
                        ]
                        .ticker
                    ),

                    "status": (
                        display
                        .get(
                            "status",
                        )

                        if (
                            display
                            is not None
                        )

                        else (
                            "ACTIVE"
                        )
                    ),

                    "quantity": (
                        display
                        .get(
                            "quantity",
                        )

                        if (
                            display
                            is not None
                        )

                        else None
                    ),

                    "positions": (
                        len(
                            orders_bought
                        )
                    ),

                    "current_price": (
                        price
                    ),

                    "realized_profit": (
                        display
                        .get(
                            "realized_profit",
                        )

                        if (
                            display
                            is not None
                        )

                        else None
                    ),

                    "unrealized_profit": (
                        display
                        .get(
                            "unrealized_profit",
                        )

                        if (
                            display
                            is not None
                        )

                        else None
                    ),

                    "total_profit": (
                        display
                        .get(
                            "total_profit",
                        )

                        if (
                            display
                            is not None
                        )

                        else None
                    ),

                    "orders_bought": (
                        orders_bought
                    ),

                    "orders_planned": (
                        orders_planned
                    ),
                }
            )

        invested = sum(
            (
                Decimal(str(asset["value"]))
                for asset in assets
                if asset["kind"] != "currency" and asset["value"] is not None
            ),
            Decimal("0"),
        )

        accounts_response\
        .append(
            {
                "id": (
                    account
                    .id
                ),

                "name": (
                    account
                    .name
                ),

                "broker": (
                    account
                    .broker
                    .value
                ),

                "mode": (
                    account
                    .mode
                    .value
                ),

                "enabled": (
                    account
                    .enabled
                ),

                "currency": (
                    currency
                ),

                "equity": (
                    float(
                        equity
                    )

                    if (
                        equity
                        is not None
                    )

                    else None
                ),

                "available": (
                    float(
                        available
                    )

                    if (
                        available
                        is not None
                    )

                    else None
                ),

                "invested": (
                    float(
                        invested
                    )
                ),

                "reserved": (
                    float(
                        reserved
                    )

                    if (
                        reserved
                        is not None
                    )

                    else None
                ),

                "balance_series": (
                    series_by_account
                    .get(
                        account
                        .id,

                        [],
                    )
                ),

                "assets": (
                    assets
                ),

                "sessions": (
                    account_sessions
                ),
            }
        )

    return {
        "accounts": (
            accounts_response
        ),
    }


# ============================================================
# COMMISSION v1.3 (п. 1)
# ============================================================

@app.get(
    "/api/commission/summary"
)
def commission_summary(
    limit: int = 50,
):
    if limit < 1:
        limit = 1

    if limit > 200:
        limit = 200

    summary = (
        commission_service
        .get_summary(
            limit=(
                limit
            ),
        )
    )

    return {
        "balance":
            summary[
                "balance"
            ],

        "forced_drain":
            summary[
                "forced_drain"
            ],

        "default_percent":
            summary[
                "default_percent"
            ],

        "by_platform":
            summary[
                "by_platform"
            ],

        "charges":
            summary[
                "charges"
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
    "/api/auth/password/reset"
)
def auth_password_reset(
    request: (
        PasswordResetRequest
    ),

    response: Response,
):
    """
    Сброс пароля кодом
    от администратора
    (головной сервер).
    """

    if (
        head_server_client
        is None
    ):
        raise HTTPException(
            status_code=503,

            detail=(
                "Сброс пароля "
                "недоступен: "
                "нет связи "
                "с головным "
                "сервером"
            ),
        )

    stored = (
        user_repository
        .get_user_by_login(
            request
            .login
            .strip()
        )
    )

    if (
        stored
        is None
    ):
        raise HTTPException(
            status_code=404,

            detail=(
                "Пользователь "
                "не найден на "
                "этом устройстве"
            ),
        )

    new_password_hash = (
        hash_password(
            request
            .password
        )
    )

    api_key, error = (
        head_server_client
        .confirm_password_reset(
            login=(
                stored
                .login
            ),

            code=(
                request
                .code
                .strip()
            ),

            new_password_hash=(
                new_password_hash
            ),
        )
    )

    if (
        error
        is not None
    ):
        raise HTTPException(
            status_code=400,

            detail=(
                error
            ),
        )

    user_repository\
        .set_user_password_hash(
            user_id=(
                stored
                .id
            ),

            password_hash=(
                new_password_hash
            ),
        )

    if api_key:
        user_repository\
            .set_user_head_api_key(
                user_id=(
                    stored
                    .id
                ),

                api_key=(
                    api_key
                ),
            )

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
            status_code=400,

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

    stored = (
        user_repository
        .get_user_by_id(
            user
            .id
        )
    )

    return {
        "user": {
            "id": (
                user
                .id
            ),

            "login": (
                user
                .login
            ),

            "full_name": (
                user
                .full_name
            ),

            "phone": (
                stored
                .phone

                if (
                    stored
                    is not None
                )

                else None
            ),

            "email": (
                stored
                .email

                if (
                    stored
                    is not None
                )

                else None
            ),

            "birth_date": (
                stored
                .birth_date

                if (
                    stored
                    is not None
                )

                else None
            ),
        }
    }


@app.patch(
    "/api/auth/profile"
)
def auth_profile_update(
    request: (
        ProfileUpdateRequest
    ),

    raw_request: Request,
):
    user, _ = (
        _auth_user(
            raw_request
        )
    )

    full_name = (
        (
            request
            .full_name
            .strip()
        )

        if (
            request
            .full_name
            is not None
        )

        else None
    )

    if (
        full_name
        == ""
    ):
        raise HTTPException(
            status_code=400,

            detail=(
                "ФИО не может "
                "быть пустым"
            ),
        )

    (
        user_repository
        .update_user_profile(
            user_id=(
                user
                .id
            ),

            full_name=(
                full_name
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
        )
    )

    updated = (
        user_repository
        .get_user_by_id(
            user
            .id
        )
    )

    return {
        "user": {
            "id": (
                user
                .id
            ),

            "login": (
                user
                .login
            ),

            "full_name": (
                updated
                .full_name

                if (
                    updated
                    is not None
                )

                else (
                    user
                    .full_name
                )
            ),

            "phone": (
                updated
                .phone

                if (
                    updated
                    is not None
                )

                else None
            ),

            "email": (
                updated
                .email

                if (
                    updated
                    is not None
                )

                else None
            ),

            "birth_date": (
                updated
                .birth_date

                if (
                    updated
                    is not None
                )

                else None
            ),
        }
    }


@app.get(
    "/api/user/head-history"
)
def user_head_history(
    request: Request,

    limit: int = 20,
):
    user, _ = (
        _auth_user(
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

    if (
        head_server_client
        is None
    ):
        return {
            "available": (
                False
            ),

            "syncs": [],
        }

    stored = (
        user_repository
        .get_user_by_id(
            user
            .id
        )
    )

    api_key = (
        stored
        .head_api_key

        if (
            stored
            is not None
        )

        else None
    )

    if (
        not api_key
    ):
        return {
            "available": (
                False
            ),

            "syncs": [],
        }

    result = (
        head_server_client
        .fetch_history(
            api_key=(
                api_key
            ),

            limit=(
                limit
            ),
        )
    )

    if (
        result
        is None
    ):
        return {
            "available": (
                False
            ),

            "syncs": [],
        }

    return {
        "available": (
            True
        ),

        "client": (
            result
            .get(
                "client",
            )
        ),

        "syncs": (
            result
            .get(
                "syncs",

                [],
            )
        ),
    }


@app.post(
    "/api/user/topup",

    status_code=201,
)
async def user_topup_create(
    request: Request,

    amount: str = Form(...),

    comment: str = Form(
        ""
    ),

    document: (
        UploadFile | None
    ) = File(
        None
    ),
):
    """
    B4: заявка на пополнение
    баланса ЛК — уходит на
    головной сервер с
    приложенным документом/
    фото; подтверждает
    администратор.
    """

    authenticated_user, _ = _auth_user(request)

    document_name = None

    document_mime = None

    document_bytes = None

    if (
        document
        is not None

        and (
            document
            .filename
        )
    ):
        document_name = (
            document
            .filename
        )

        document_mime = (
            document
            .content_type
        )

        document_bytes = (
            await (
                document
                .read()
            )
        )

    if user_repository.get_user_head_api_key(authenticated_user.id) is None:
        head_replication_worker.retry_pending_head_users()

    created, error = (
        topup_service
        .submit_topup(
            user_id=authenticated_user.id,
            amount_raw=(
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

            document_bytes=(
                document_bytes
            ),
        )
    )

    if (
        created
        is None
        or error
    ):
        unavailable = (
            error
            and (
                "недоступен"
                in error
            )
        ) or (
            error
            and (
                "не зарегистрирован"
                in error
                or "ещё не подтверждена" in error
            )
        )

        raise HTTPException(
            status_code=(
                503
                if unavailable
                else 400
            ),

            detail=(
                error
                or (
                    "Не удалось "
                    "отправить заявку"
                )
            ),
        )

    return {
        "request": (
            created
        ),

        "balance": (
            str(
                commission_repository
                .get_balance()
            )
        ),
    }


@app.get(
    "/api/user/topups"
)
def user_topups(
    request: Request,

    limit: int = 20,
):
    """
    B4: статусы заявок на
    пополнение. Подтягивает
    актуальное состояние с
    головы и зачисляет
    подтверждённые суммы.
    """

    _auth_user(
        request
    )

    if limit < 1:
        limit = 1

    if limit > 100:
        limit = 100

    result = (
        topup_service
        .refresh_topups()
    )

    if (
        result
        is None
    ):
        return {
            "available": (
                False
            ),

            **(
                topup_service
                .list_local(
                    limit=(
                        limit
                    ),
                )
            ),
        }

    return {
        "available": (
            True
        ),

        **(
            result
        ),
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

def _operations_feed_sort_key(
    item: dict,
) -> datetime:
    raw = (
        item[
            "created_at"
        ]
    )

    try:
        parsed = (
            datetime
            .fromisoformat(
                raw
            )
        )

    except (
        TypeError,
        ValueError,
    ):
        return (
            datetime
            .min
            .replace(
                tzinfo=timezone.utc,
            )
        )

    if (
        parsed
        .tzinfo
        is None
    ):
        parsed = (
            parsed
            .replace(
                tzinfo=timezone.utc,
            )
        )

    return parsed


@app.get("/api/bybit/accounts/{account_id}/asset-rules/{symbol}")
def bybit_asset_rules(account_id: str, symbol: str):
    try:
        account = trading_account_service.get(account_id)
        if account.broker != BrokerType.BYBIT or account.mode != TradingAccountMode.LIVE or not account.enabled:
            raise ValueError("Выберите активный боевой счёт Bybit")
        adapter = broker_registry.get(BrokerType.BYBIT)
        if not isinstance(adapter, AssetRulesProvider):
            raise ValueError("Платформа не поддерживает получение правил актива")
        return adapter.asset_rules(trading_account_service.get_credentials(account_id), symbol.upper())
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Счёт не найден") from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/api/grid-history")
def grid_history():
    return {"grids": trading_state_repository.closed_grids()}


@app.get(
    "/api/operations"
)
def operations(
    limit: int | None = None,
):
    safe_limit = max(1, min(limit, 500)) if limit is not None else 1000000
    since = (
        datetime.now(timezone.utc) - timedelta(days=BALANCE_SNAPSHOT_RETENTION_DAYS)
    ).isoformat()
    broker_operations = broker_cash_flow_repository.operations_since(since)
    imported_flows = {
        (account_id, operation.occurred_at.isoformat(), operation.kind,
         operation.currency, operation.payment)
        for account_id, operation in broker_operations
        if operation.kind in EXTERNAL_FLOW_KINDS
    }

    items = [
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

    #
    # Внешние потоки по счетам
    # брокеров: пополнения и выводы.
    #
    for flow in (
        broker_cash_flow_repository
        .get_since(since)
    ):
        if (flow.trading_account_id, flow.occurred_at, flow.kind,
            flow.currency, flow.payment) in imported_flows:
            continue
        is_deposit = (
            flow
            .payment
            > 0
        )

        amount = (
            abs(
                flow
                .payment
            )
        )

        items.append(
            {
                "created_at":
                    flow
                    .occurred_at,

                "trading_account_id":
                    flow
                    .trading_account_id,

                "instrument_id":
                    None,

                "ticker":
                    flow
                    .currency,

                "event_type": (
                    "DEPOSIT"

                    if is_deposit

                    else "WITHDRAWAL"
                ),

                "details": (
                    f"пополнение {amount} {flow.currency}"

                    if is_deposit

                    else f"вывод {amount} {flow.currency}"
                ),
            }
        )

    #
    # Комиссии Личного кабинета.
    #
    for charge in (
        commission_repository
        .recent(
            limit=safe_limit,
        )
    ):
        items.append(
            {
                "created_at":
                    charge
                    .created_at,

                "trading_account_id":
                    charge
                    .trading_account_id,

                "instrument_id":
                    charge
                    .instrument_id,

                "ticker":
                    charge
                    .ticker,

                "event_type":
                    "COMMISSION",

                "details": (
                    f"списание комиссии ЛК −{charge.amount} ₽ · {charge.percent}% · "
                    f"прибыль={charge.trade_profit} ₽ · "
                    f"баланс={charge.balance_after} ₽"
                ),
            }
        )

    for account_id, operation in broker_operations:
        if operation.kind in EXTERNAL_FLOW_KINDS:
            event_type = "DEPOSIT" if operation.payment > 0 else "WITHDRAWAL"
            action = "пополнение" if operation.payment > 0 else "вывод"
            details = f"{action} {abs(operation.payment)} {operation.currency}"
        else:
            event_type = {
                "buy": "BUY", "buycard": "BUY", "buymargin": "BUY",
                "sell": "SELL", "sellcard": "SELL", "sellmargin": "SELL",
                "brokerfee": "BROKER_COMMISSION", "servicefee": "BROKER_COMMISSION",
                "dividend": "DIVIDEND", "coupon": "COUPON", "tax": "TAX",
            }.get(operation.kind, "BROKER_OPERATION")
            details = f"{operation.kind}: {operation.payment} {operation.currency}"
            if operation.quantity is not None:
                details += f" · количество={operation.quantity}"
        items.append({
            "created_at": operation.occurred_at.isoformat(),
            "trading_account_id": account_id,
            "instrument_id": operation.instrument_id,
            "ticker": operation.ticker or operation.currency,
            "event_type": event_type,
            "details": details,
            "source": "broker",
            "operation_id": operation.operation_id,
        })

    items.sort(
        key=_operations_feed_sort_key,

        reverse=True,
    )

    return {
        "operations": (
            items[
                :safe_limit
            ]
        ),
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
            cleaned is None
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


class GridPreviewInstrumentRequest(BaseModel):
    ticker: str
    levels: int = Field(default=30, ge=5, le=30)
    quantity: int = Field(default=1, ge=1)


class GridPreviewRequest(BaseModel):
    capital: Decimal = Field(gt=0)
    instruments: list[GridPreviewInstrumentRequest]
    trading_account_id: str | None = None


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

    min_levels: int = 5

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


@app.post("/api/instrument-selection/grids")
def instrument_selection_grids(request: GridPreviewRequest):
    from application.auto_portfolio_selector import GridSelectionPlan, _to_selection
    from application.portfolio_capital_calculator import PortfolioCapitalCalculator

    tickers = [item.ticker.strip().upper() for item in request.instruments]
    if any(not ticker for ticker in tickers) or len(set(tickers)) != len(tickers):
        raise HTTPException(status_code=400, detail="Instrument tickers must be nonempty and unique")
    try:
        snapshots = instrument_market_service.get_snapshots(
            tickers=tickers,
            trading_account_id=request.trading_account_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=502, detail="Market data unavailable") from error

    available = {item.ticker.strip().upper(): item for item in snapshots}
    calculator = PortfolioCapitalCalculator()
    plan = GridSelectionPlan(capital=request.capital)
    for item, ticker in zip(request.instruments, tickers):
        snapshot = available.get(ticker)
        if snapshot is None or snapshot.price <= 0:
            raise HTTPException(status_code=400, detail=f"No price for instrument {ticker}")
        cost = calculator.calculate(
            min_price=snapshot.price * Decimal("0.70"),
            current_price=snapshot.price,
            levels_count=item.levels,
            base_quantity=item.quantity,
        )
        selection = _to_selection(snapshot, item.quantity, item.levels, cost)
        selection.ticker = ticker
        plan.selections.append(selection)
    return _grid_selection_plan_response(mode="manual", index_id=None, plan=plan)


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

    except KeyError:
        for platform in platform_connection_service.get_all():
            if platform.broker == BrokerType.TINVEST and platform.mode.value == state.mode.lower():
                return platform_connection_service.get_credentials(platform.id).get("token")
        return settings.tinvest_token if state.mode.lower() == "live" else settings.tinvest_sandbox_token
    except (ValueError, OSError):
        return None


@app.get(
    "/api/session"
    "/{ticker}/chart"
)
def session_chart(
    ticker: str,

    days: int = 60,

    interval: str = "15m",
):
    normalized = (
        ticker
        .upper()
    )

    safe_interval = (
        interval
        .strip()
        .lower()
    )

    interval_limits = {
        "15m": 7,

        "1h": 30,

        "4h": 90,

        "1d": 365,
    }

    if (
        safe_interval
        not in interval_limits
    ):
        safe_interval = (
            "1d"
        )

    safe_days = (
        max(
            7,

            min(
                days,

                interval_limits[
                    safe_interval
                ],
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
    session_started_at = _parse_snapshot_timestamp(getattr(state, "started_at", None))
    chart_since = session_started_at or (
        datetime.now(timezone.utc) - timedelta(days=safe_days)
    )

    if (
        state
        is not None
        and instrument_state is not None
    ):
        chart_account = None
        try:
            chart_account = trading_account_service.get(state.trading_account_id)
        except KeyError:
            pass
        if chart_account is not None and chart_account.broker == BrokerType.BYBIT:
            from infrastructure.bybit.client import BybitClient
            from domain.entities import Candle

            credentials = trading_account_service.get_credentials(chart_account.id)
            client = BybitClient(credentials.require("api_key"), credentials.require("api_secret"))
            bybit_interval = {"1m": "1", "5m": "5", "15m": "15", "1h": "60", "4h": "240", "1d": "D"}.get(safe_interval, "15")
            end = int(datetime.now(timezone.utc).timestamp() * 1000)
            start = int(chart_since.timestamp() * 1000)
            seen_times = set()
            while end >= start:
                rows = client.get_klines(normalized, bybit_interval, 1000, start, end)
                if not rows:
                    break
                earliest = min(int(row[0]) for row in rows)
                for row in rows:
                    timestamp = int(row[0])
                    if timestamp in seen_times:
                        continue
                    seen_times.add(timestamp)
                    candles.append(Candle(normalized, Decimal(row[1]), Decimal(row[2]), Decimal(row[3]), Decimal(row[4]), 0, datetime.fromtimestamp(timestamp / 1000, timezone.utc)))
                if earliest > end:
                    raise ValueError("Bybit candle pagination did not advance")
                end = earliest - 1
            candles.sort(key=lambda candle: candle.timestamp)
            token = None
        else:
            token = _resolve_chart_token(state)

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
                    .get_candles(
                        instrument_id=(
                            instrument_state
                            .instrument_uid
                        ),

                        date_from=chart_since,

                        date_to=(
                            now
                        ),

                        interval=(
                            safe_interval
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

    candles = [candle for candle in candles if candle.timestamp >= chart_since]
    trades = []

    for event in operation_log_repository.get_since(since=chart_since.isoformat()):
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
        if state is not None and event.trading_account_id not in (None, state.trading_account_id):
            continue
        event_time = _parse_snapshot_timestamp(event.created_at)
        if event_time is None or event_time < chart_since:
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

        "interval":
            safe_interval,

        "session_id": (
            state
            .session_id

            if (
                state
                is not None
            )

            else None
        ),

        "started_at": session_started_at.isoformat() if session_started_at else None,

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
    runners = web_runner_registry.get_by_ticker(ticker)
    if runners:
        for runner in runners:
            runner.request_market_stop()
        return {"ticker": ticker.upper(), "status": "STOPPING", "removed": False}
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
    _ensure_commission_allows_start()

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
            platform=account.broker.value,
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
    _ensure_commission_allows_start()

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
    token = None

    account_id = None

    for account in (
        trading_account_service
        .get_all()
    ):
        if (
            not account.enabled
            or account.mode
            != TradingAccountMode.LIVE
            or account.broker
            != BrokerType.TINVEST
        ):
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

        except Exception as error:
            print(
                "LIVE STATUS CREDENTIALS ERROR:",
                account.id,
                repr(
                    error,
                ),
            )

            continue

        account_id = (
            account
            .broker_account_id
            or None
        )

        break

    status = (
        LiveAccountService(
            settings=settings,

            token=(
                token
            ),

            account_id=(
                account_id
            ),
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
                    push_notifier
                ),

                commission_service=(
                    commission_service
                ),

                broker=(
                    sandbox_account
                    .broker
                    .value
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

                commission_service=(
                    commission_service
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

        "base_currency":
            account
            .base_currency,

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

    if (
        broker
        == BrokerType.BYBIT
    ):
        return {
            "id":
                broker.value,

            "name":
                "Bybit",

            "supported":
                supported,

            "credential_fields": [
                {
                    "key":
                        "api_key",

                    "label":
                        "API Key",

                    "type":
                        "text",

                    "required":
                        True,
                },

                {
                    "key":
                        "api_secret",

                    "label":
                        "API Secret",

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
    platform: str = "tinvest",
) -> MultiInstrumentSessionConfig:
    return trading_settings_service.apply_to_config(
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
                    base_order_amount=instrument.base_order_amount,
                )
                for instrument
                in instruments
            ],
        ),
        platform,
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

                    commission_service=(
                        commission_service
                    ),

                    broker="tinvest",
                    trading_settings_service=trading_settings_service,
                    instrument_availability_check=(
                        lambda ticker: web_runner_registry.ensure_instruments_available(
                            trading_account_id, [ticker]
                        )
                    ) if trading_account_id is not None else None,
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
