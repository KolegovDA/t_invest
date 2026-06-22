import os
from decimal import Decimal
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from application.multi_instrument_session_config import (
    InstrumentConfig,
    MultiInstrumentSessionConfig,
)
from application.multi_instrument_trading_session_factory import (
    MultiInstrumentTradingSessionFactory,
)
from application.portfolio_orchestrator import PortfolioOrchestrator
from application.sandbox_session_registry import (
    SandboxSessionSnapshot,
    sandbox_session_registry,
)
from application.web_runner_registry import web_runner_registry
from application.web_runner_service import WebRunnerService
from config.settings import Settings
from infrastructure.sqlite.api_usage_repository import (
    SQLiteApiUsageRepository,
)
from infrastructure.sqlite.sqlite_database import SQLiteDatabase
from infrastructure.sqlite.web_session_repository import (
    SQLiteWebSessionRepository,
)
from web.session_registry import WebSession, session_registry

APP_VERSION = "1.0.0-mvp"

settings = Settings.from_env()

database_path = Path(
    os.getenv(
        "T_INVEST_DB_PATH",
        settings.db_path,
    )
)

database = SQLiteDatabase(
    database_path=database_path,
)
database.initialize()

session_registry.repository = SQLiteWebSessionRepository(
    database=database,
)
session_registry.load_from_repository()

api_usage_repository = SQLiteApiUsageRepository(
    database=database,
)

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


class StartPlanInstrumentRequest(BaseModel):
    ticker: str
    levels: int
    quantity: int


class StartPlanRequest(BaseModel):
    available_cash: Decimal
    instruments: list[StartPlanInstrumentRequest]


class StartSandboxRequest(BaseModel):
    force: bool = False
    instruments: list[StartPlanInstrumentRequest]


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "real_sandbox_enabled": _is_real_sandbox_enabled(),
    }


@app.get("/api/version")
def version():
    return {
        "version": APP_VERSION,
    }


@app.get("/api/dashboard")
def dashboard():
    sessions = [
        _build_display_session(
            web_session=session,
        )
        for session in session_registry.get_sessions()
    ]

    return {
        "accounts": 1,
        "capital": 100000,
        "active_positions": sum(
            session["positions"]
            for session in sessions
        ),
        "profit": sum(
            session["total_profit"]
            for session in sessions
        ),
        "instruments": [
            session["ticker"]
            for session in sessions
        ],
    }


@app.get("/api/api-usage")
def api_usage():
    summary = api_usage_repository.summarize()

    return {
        "total_weight": summary.total_weight,
        "events_count": summary.events_count,
        "by_operation": summary.by_operation,
    }


@app.get("/api/instruments")
def instruments():
    return {
        "instruments": [
            {
                "ticker": "SBER",
                "levels": 20,
                "price": 317,
                "required_capital": 7774,
            },
            {
                "ticker": "GAZP",
                "levels": 20,
                "price": 107,
                "required_capital": 3080,
            },
            {
                "ticker": "LKOH",
                "levels": 20,
                "price": 4453,
                "required_capital": 128540,
            },
        ],
    }


@app.get("/api/sessions")
def sessions():
    return {
        "sessions": [
            _build_display_session(
                web_session=session,
            )
            for session in session_registry.get_sessions()
        ],
    }


@app.get("/api/session/{ticker}")
def session_detail(
    ticker: str,
):
    try:
        web_session = session_registry.get_session(
            ticker=ticker,
        )
    except KeyError as error:
        raise HTTPException(
            status_code=404,
            detail=f"Session not found: {ticker.upper()}",
        ) from error

    return _build_display_session(
        web_session=web_session,
    )


@app.post("/api/stop-session/{ticker}")
def stop_session(
    ticker: str,
):
    web_runner_registry.stop_by_ticker(
        ticker=ticker,
    )

    sandbox_session_registry.unregister(
        ticker=ticker,
    )

    try:
        session = session_registry.stop_session(
            ticker=ticker,
        )
    except KeyError as error:
        raise HTTPException(
            status_code=404,
            detail=f"Session not found: {ticker.upper()}",
        ) from error

    if session is None:
        return {
            "ticker": ticker.upper(),
            "status": "REMOVED",
            "removed": True,
        }

    return {
        **_build_display_session(
            web_session=session,
        ),
        "removed": False,
    }


@app.post("/api/start-plan")
def start_plan(
    request: StartPlanRequest,
):
    api_usage_repository.record(
        source="web",
        operation="start_plan",
        weight=1,
    )

    config = _build_multi_instrument_config(
        instruments=request.instruments,
    )

    prices_by_ticker: dict[str, Decimal] = {}
    price_ranges_by_ticker: dict[str, tuple[Decimal, Decimal]] = {}

    for instrument in request.instruments:
        ticker = instrument.ticker.upper()
        current_price = _get_mock_price(
            ticker=ticker,
        )

        prices_by_ticker[ticker] = current_price
        price_ranges_by_ticker[ticker] = (
            current_price * Decimal("0.70"),
            current_price * Decimal("1.10"),
        )

        api_usage_repository.record(
            source="mock",
            operation="get_last_price",
            weight=1,
            ticker=ticker,
        )

    plan = PortfolioOrchestrator().build_start_plan(
        config=config,
        price_ranges_by_ticker=price_ranges_by_ticker,
        prices_by_ticker=prices_by_ticker,
        available_cash=request.available_cash,
    )

    return {
        "available_cash": str(plan.available_cash),
        "total_required": str(plan.total_required_deposit),
        "remaining_cash": str(plan.remaining_cash),
        "missing_cash": str(plan.missing_cash),
        "can_start": plan.can_start,
        "can_start_forced": plan.can_start_forced,
        "capital_utilization_percent": str(
            plan.capital_utilization_percent,
        ),
        "instruments": [
            {
                "ticker": instrument.ticker,
                "levels": instrument.levels_count,
                "quantity": instrument.quantity,
                "last_price": str(instrument.last_price),
                "required_deposit": str(instrument.required_deposit),
            }
            for instrument in plan.instruments
        ],
    }


@app.post("/api/start-sandbox")
def start_sandbox(
    request: StartSandboxRequest,
):
    api_usage_repository.record(
        source="web",
        operation="start_sandbox",
        weight=1,
    )

    started_sessions = [
        session_registry.start_session(
            ticker=instrument.ticker,
            levels=instrument.levels,
            quantity=instrument.quantity,
        )
        for instrument in request.instruments
    ]

    real_sandbox_status = "disabled"

    if _is_real_sandbox_enabled():
        real_sandbox_status = _try_start_real_sandbox(
            request=request,
        )

    return {
        "status": "started",
        "mode": "sandbox",
        "real_sandbox_status": real_sandbox_status,
        "force": request.force,
        "sessions": [
            _build_display_session(
                web_session=session,
            )
            for session in started_sessions
        ],
    }


def _try_start_real_sandbox(
    request: StartSandboxRequest,
) -> str:
    try:
        config = _build_multi_instrument_config(
            instruments=request.instruments,
        )

        context = MultiInstrumentTradingSessionFactory(
            settings=settings,
        ).create_sandbox_session(
            config=config,
        )

        runner = WebRunnerService(
            context=context,
            api_usage_repository=api_usage_repository,
            polling_interval_seconds=10,
        )

        web_runner_registry.start(
            runner=runner,
        )

        api_usage_repository.record(
            source="runner",
            operation="real_sandbox_started",
            weight=1,
        )

        return "started"

    except Exception as error:
        api_usage_repository.record(
            source="runner",
            operation="real_sandbox_start_failed",
            weight=1,
        )

        print(
            "REAL SANDBOX START FAILED:",
            repr(error),
        )

        return "fallback_mock"


def _build_multi_instrument_config(
    instruments: list[StartPlanInstrumentRequest],
) -> MultiInstrumentSessionConfig:
    return MultiInstrumentSessionConfig(
        instruments=[
            InstrumentConfig(
                ticker=instrument.ticker.upper(),
                levels_count=instrument.levels,
                quantity=instrument.quantity,
            )
            for instrument in instruments
        ]
    )


def _is_real_sandbox_enabled() -> bool:
    if os.getenv("PYTEST_CURRENT_TEST"):
        return False

    return settings.web_real_sandbox


def _build_display_session(
    web_session: WebSession,
):
    snapshot = sandbox_session_registry.build_snapshot(
        ticker=web_session.ticker,
    )

    if snapshot is not None:
        return _snapshot_to_dict(
            snapshot=snapshot,
            web_session=web_session,
        )

    return _web_session_to_dict(
        session=web_session,
    )


def _snapshot_to_dict(
    snapshot: SandboxSessionSnapshot,
    web_session: WebSession,
):
    return {
        "ticker": snapshot.ticker,
        "levels": web_session.levels,
        "quantity": snapshot.quantity,
        "status": snapshot.status,
        "positions": snapshot.positions,
        "current_price": float(snapshot.current_price),
        "realized_profit": float(snapshot.realized_profit),
        "unrealized_profit": float(snapshot.unrealized_profit),
        "total_profit": float(snapshot.total_profit),
    }


def _web_session_to_dict(
    session: WebSession,
):
    return {
        "ticker": session.ticker,
        "levels": session.levels,
        "quantity": session.quantity,
        "status": session.status,
        "positions": session.positions,
        "current_price": session.current_price,
        "realized_profit": session.realized_profit,
        "unrealized_profit": session.unrealized_profit,
        "total_profit": session.total_profit,
    }


def _get_mock_price(
    ticker: str,
) -> Decimal:
    prices = {
        "SBER": Decimal("317"),
        "GAZP": Decimal("107"),
        "LKOH": Decimal("4453"),
        "VTBR": Decimal("0.09"),
    }

    return prices.get(
        ticker,
        Decimal("100"),
    )
