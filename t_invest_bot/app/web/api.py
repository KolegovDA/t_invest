from pathlib import Path

from fastapi import Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from web.api import app

FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"

if FRONTEND_DIST.exists():
    app.mount(
        "/assets",
        StaticFiles(directory=FRONTEND_DIST / "assets"),
        name="assets",
    )


@app.get("/{full_path:path}")
def serve_frontend(full_path: str, request: Request):
    if full_path.startswith("api/"):
        return {
            "detail": "Not found",
        }

    index_file = FRONTEND_DIST / "index.html"

    if index_file.exists():
        return FileResponse(index_file)

    return {
        "detail": "Frontend build not found. Run: npm run build",
    }
