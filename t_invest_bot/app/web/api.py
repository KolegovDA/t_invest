from __future__ import annotations

import hashlib
import json
import os

from decimal import Decimal

from fastapi import (
    FastAPI,
    HTTPException,
)
from fastapi.middleware.cors import (
    CORSMiddleware,
)
from pydantic import BaseModel

from application.live_account_service import (
    LiveAccountService,
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
from application.trading_mode_guard import (
    TradingModeGuard,
)
from application.trading_session_state_service import (
    TradingSessionStateService,
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

from infrastructure.sqlite.api_usage_repository import (
    SQLiteApiUsageRepository,
)
from infrastructure.sqlite.sqlite_database import (
    SQLiteDatabase,
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

#
# КРИТИЧНО:
#
# Путь к БД больше не зависит
# от текущей рабочей директории.
#
# Python:
#   <project>/data/tinvest.db
#
# PyInstaller:
#   <exe_dir>/data/tinvest.db
#
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
# FASTAPI
# ============================================================

app = FastAPI(
    title="T-Invest Bot API",
    version=APP_VERSION,
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
    available_cash: Decimal

    instruments: list[
        StartPlanInstrumentRequest
    ]


class StartSandboxRequest(
    BaseModel
):
    force: bool = False

    instruments: list[
        StartPlanInstrumentRequest
    ]


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

    guard = TradingModeGuard(
        settings=settings,
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

    runner = None

    try:
        context = (
            MultiInstrumentTradingSessionFactory(
                settings=settings,
            )
            .create_live_session(
                config=config,
            )
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

        trading_account_id = (
            _build_trading_account_id(
                mode="live",

                broker_account_id=(
                    context.account_id
                ),
            )
        )

        runner = WebRunnerService(
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

        web_runner_registry.start(
            runner=runner,
        )

    except Exception as error:
        api_usage_repository.record(
            source="runner",
            operation=(
                "live_start_failed"
            ),
            weight=1,
        )

        print(
            "LIVE START FAILED:",
            repr(
                error
            ),
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Live trading session "
                f"failed: {error!r}"
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

        api_usage_repository.record(
            source="runner",
            operation="live_started",
            weight=1,
        )

    except Exception:
        if runner is not None:
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

        "account_id": (
            settings
            .tinvest_live_account_id
        ),

        "runner_session_id": (
            runner.session_id
            if runner is not None
            else None
        ),

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

        "trading_mode": (
            settings
            .trading_mode
        ),

        "live_trading_enabled": (
            settings
            .live_trading_enabled
        ),

        "real_sandbox_enabled": (
            _is_real_sandbox_enabled()
        ),

        "state_persistence_enabled":
            True,

        "database_path":
            str(
                database_path
            ),
    }


# ============================================================
# VERSION
# ============================================================

@app.get(
    "/api/version"
)
def version():
    return {
        "version":
            APP_VERSION,
    }


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

    return {
        "accounts":
            1,

        "capital":
            100000,

        "active_positions": sum(
            session[
                "positions"
            ]
            for session
            in sessions
        ),

        "profit": sum(
            session[
                "total_profit"
            ]
            for session
            in sessions
        ),

        "instruments": [
            session[
                "ticker"
            ]
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
# RUNNER STATUS
# ============================================================

@app.get(
    "/api/runner-status"
)
def runner_status():
    return {
        "runners": [
            {
                "session_id": (
                    runner
                    .session_id
                ),

                "trading_account_id": (
                    runner
                    .trading_account_id
                ),

                "is_running": (
                    status
                    .is_running
                ),

                "last_tick_at": (
                    status
                    .last_tick_at
                ),

                "last_error": (
                    status
                    .last_error
                ),

                "ticks_count": (
                    status
                    .ticks_count
                ),

                "prices_checked_total": (
                    status
                    .prices_checked_total
                ),

                "orders_placed_total": (
                    status
                    .orders_placed_total
                ),

                "executions_total": (
                    status
                    .executions_total
                ),
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
    return {
        "instruments": [
            {
                "ticker":
                    "SBER",

                "levels":
                    20,

                "price":
                    317,

                "required_capital":
                    7774,
            },

            {
                "ticker":
                    "GAZP",

                "levels":
                    20,

                "price":
                    107,

                "required_capital":
                    3080,
            },

            {
                "ticker":
                    "LKOH",

                "levels":
                    20,

                "price":
                    4453,

                "required_capital":
                    128540,
            },
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

    return _build_display_session(
        web_session=(
            web_session
        ),
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
# START PLAN
# ============================================================

@app.post(
    "/api/start-plan"
)
def start_plan(
    request: StartPlanRequest,
):
    api_usage_repository.record(
        source="web",
        operation="start_plan",
        weight=1,
    )

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

        api_usage_repository.record(
            source="mock",
            operation=(
                "get_last_price"
            ),
            weight=1,
            ticker=ticker,
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
                request
                .available_cash
            ),
        )
    )

    return {
        "available_cash":
            str(
                plan
                .available_cash
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
            plan
            .can_start,

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
                    instrument
                    .ticker,

                "levels":
                    instrument
                    .levels_count,

                "quantity":
                    instrument
                    .quantity,

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
# SANDBOX START
# ============================================================

@app.post(
    "/api/start-sandbox"
)
def start_sandbox(
    request: StartSandboxRequest,
):
    api_usage_repository.record(
        source="web",
        operation="start_sandbox",
        weight=1,
    )

    started_sessions = [
        session_registry
        .start_session(
            ticker=(
                instrument
                .ticker
            ),

            levels=(
                instrument
                .levels
            ),

            quantity=(
                instrument
                .quantity
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
                    account
                    .name,

                "status":
                    account
                    .status,

                "account_type":
                    account
                    .account_type,

                "selected":
                    account
                    .selected,
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
                status
                .portfolio
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
            status
            .error,
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
                    request
                    .instruments
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
                    request
                    .instruments
                ),
            )
        )

        trading_account_id = (
            _build_trading_account_id(
                mode="sandbox",

                broker_account_id=(
                    context.account_id
                ),
            )
        )

        runner = WebRunnerService(
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

        web_runner_registry.start(
            runner=runner,
        )

        api_usage_repository.record(
            source="runner",
            operation=(
                "real_sandbox_started"
            ),
            weight=1,
        )

        return "started"

    except Exception as error:
        api_usage_repository.record(
            source="runner",
            operation=(
                "real_sandbox_start_failed"
            ),
            weight=1,
        )

        print(
            "REAL SANDBOX START FAILED:",
            repr(
                error
            ),
        )

        return "fallback_mock"


# ============================================================
# CONFIG HELPERS
# ============================================================

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
                        instrument
                        .levels
                    ),

                    quantity=(
                        instrument
                        .quantity
                    ),
                )
                for instrument
                in instruments
            ],
        )
    )


# ============================================================
# STABLE SESSION ID
# ============================================================

def _build_runner_session_id(
    mode: str,

    broker_account_id: str,

    instruments: list[
        StartPlanInstrumentRequest
    ],
) -> str:
    normalized_instruments = [
        {
            "ticker": (
                instrument
                .ticker
                .upper()
            ),

            "levels": int(
                instrument
                .levels
            ),

            "quantity": int(
                instrument
                .quantity
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
            mode
            .lower(),

        "broker_account_id":
            str(
                broker_account_id
            ),

        "instruments":
            normalized_instruments,
    }

    serialized = json.dumps(
        payload,

        ensure_ascii=False,

        sort_keys=True,

        separators=(
            ",",
            ":",
        ),
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


# ============================================================
# ENVIRONMENT
# ============================================================

def _is_real_sandbox_enabled() -> bool:
    if os.getenv(
        "PYTEST_CURRENT_TEST"
    ):
        return False

    return (
        settings
        .web_real_sandbox
    )


# ============================================================
# DISPLAY SESSION
# ============================================================

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
        return (
            _snapshot_to_dict(
                snapshot=snapshot,

                web_session=(
                    web_session
                ),
            )
        )

    return (
        _web_session_to_dict(
            session=(
                web_session
            ),
        )
    )


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
            session.current_price,

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


# ============================================================
# MOCK PRICES
# ============================================================

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

    return prices.get(
        ticker,

        Decimal(
            "100"
        ),
    )
