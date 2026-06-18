from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


@app.get("/api/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
    }


@app.get("/api/version")
def version() -> dict[str, str]:
    return {
        "version": APP_VERSION,
        "stage": "mvp",
    }


@app.get("/api/accounts")
def accounts() -> dict[str, list[dict[str, str]]]:
    return {
        "accounts": [],
    }


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "T-Invest Bot API",
        "health": "/api/health",
        "version": "/api/version",
        "accounts": "/api/accounts",
    }
