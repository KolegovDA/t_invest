from decimal import Decimal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from application.multi_instrument_session_config import (
    InstrumentConfig,
    MultiInstrumentSessionConfig,
)
from application.portfolio_orchestrator import PortfolioOrchestrator
from web.session_registry import WebSession, session_registry

APP_VERSION = "1.0.0-mvp"

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
    }


@app.get("/api/version")
def version():
    return {
        "version": APP_VERSION,
    }


@app.get("/api/dashboard")
def dashboard():
    sessions = session_registry.get_sessions()

    return {
        "accounts": 1,
        "capital": 100000,
        "active_positions": sum(
            session.positions
            for session in sessions
        ),
        "profit": sum(
            session.total_profit
            for session in sessions
        ),
        "instruments": [
            session.ticker
            for session in sessions
        ],
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
            _session_to_dict(session)
            for session in session_registry.get_sessions()
        ],
    }


@app.get("/api/session/{ticker}")
def session_detail(
    ticker: str,
):
    try:
        session = session_registry.get_session(
            ticker=ticker,
        )
    except KeyError as error:
        raise HTTPException(
            status_code=404,
            detail=f"Session not found: {ticker.upper()}",
        ) from error

    return _session_to_dict(session)


@app.post("/api/stop-session/{ticker}")
def stop_session(
    ticker: str,
):
    try:
        session = session_registry.stop_session(
            ticker=ticker,
        )
    except KeyError as error:
        raise HTTPException(
            status_code=404,
            detail=f"Session not found: {ticker.upper()}",
        ) from error

    return _session_to_dict(session)


@app.post("/api/start-plan")
def start_plan(
    request: StartPlanRequest,
):
    config = MultiInstrumentSessionConfig(
        instruments=[
            InstrumentConfig(
                ticker=instrument.ticker.upper(),
                levels_count=instrument.levels,
                quantity=instrument.quantity,
            )
            for instrument in request.instruments
        ]
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
    started_sessions = [
        session_registry.start_session(
            ticker=instrument.ticker,
            levels=instrument.levels,
            quantity=instrument.quantity,
        )
        for instrument in request.instruments
    ]

    return {
        "status": "started",
        "mode": "sandbox",
        "force": request.force,
        "sessions": [
            _session_to_dict(session)
            for session in started_sessions
        ],
    }


def _session_to_dict(
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
