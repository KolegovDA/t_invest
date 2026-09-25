from __future__ import annotations

import hashlib
import json
import os

from contextlib import asynccontextmanager
from decimal import Decimal

from fastapi import (
    FastAPI,
    HTTPException,
)
from fastapi.middleware.cors import (
    CORSMiddleware,
)
from pydantic import (
    BaseModel,
)

from application.live_account_service import (
    LiveAccountService,
)
from application.instrument_catalog_service import (
    InstrumentCatalogService,
)
from application.live_start_validation_service import (
    LiveStartValidationService,
)
from application.multi_instrument_session_config import (
    InstrumentConfig,
    MultiInstrumentSessionConfig,
)
from application.multi_instrument_trading_session_factory import (
    MultiInstrumentTradingSessionFactory,
)
from application.portfolio_orchestrator import (
    PortfolioOrchestrator,
)
from application.sandbox_session_registry import (
    SandboxSessionSnapshot,
    sandbox_session_registry,
)
from application.trading_account_service import (
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
from infrastructure.sqlite.sqlite_database import (
    SQLiteDatabase,
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


APP_VERSION = "1.1.0-dev"


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
    )
)


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


# ============================================================
# BROKER REGISTRY
# ============================================================

broker_registry = (
    create_default_broker_registry()
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

    return (
        _trading_account_to_dict(
            account
        )
    )


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

        runner = (
            WebRunnerService(
                context=context,

                api_usage_repository=(
                    api_usage_repository
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

    if (
        request.trading_account_id
        is not None
    ):
        try:
            account = (
                trading_account_service
                .get(
                    request
                    .trading_account_id
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
            str(
                plan.available_cash
            ),

        "total_required":
            str(
                plan
                .total_required_deposit
            ),

        "remaining_cash":
            str(
                plan
                .remaining_cash
            ),

        "missing_cash":
            str(
                plan
                .missing_cash
            ),

        "can_start":
            plan.can_start,

        "can_start_forced":
            plan
            .can_start_forced,

        "capital_utilization_percent":
            str(
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
                    str(
                        instrument
                        .last_price
                    ),

                "required_deposit":
                    str(
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
        real_sandbox_status = (
            _try_start_real_sandbox(
                request=request,
            )
        )

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

        context = (
            MultiInstrumentTradingSessionFactory(
                settings=settings,
            )
            .create_sandbox_session(
                config=config,
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

        trading_account_id = (
            request
            .trading_account_id
        )

        if (
            trading_account_id
            is None
        ):
            trading_account_id = (
                _build_trading_account_id(
                    mode="sandbox",

                    broker_account_id=(
                        context.account_id
                    ),
                )
            )

        runner = (
            WebRunnerService(
                context=context,

                api_usage_repository=(
                    api_usage_repository
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
            )
        )

        web_runner_registry.start(
            runner=runner,
        )

        return (
            "started"
        )

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


# ============================================================
# HELPERS
# ============================================================

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
