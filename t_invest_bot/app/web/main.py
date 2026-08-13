from pathlib import Path
import sys

from fastapi import HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from web.api import app


def get_frontend_dist() -> Path:
    if getattr(sys, "frozen", False):
        bundle_root = Path(sys._MEIPASS)

        return (
            bundle_root
            / "frontend"
            / "dist"
        )

    return (
        Path(__file__).resolve().parents[2]
        / "frontend"
        / "dist"
    )


FRONTEND_DIST = get_frontend_dist()

ASSETS_DIR = (
    FRONTEND_DIST
    / "assets"
)


if ASSETS_DIR.exists():
    app.mount(
        "/assets",
        StaticFiles(
            directory=ASSETS_DIR,
            check_dir=True,
        ),
        name="assets",
    )


@app.get("/api/frontend-debug")
def frontend_debug():
    return {
        "frozen": bool(
            getattr(sys, "frozen", False)
        ),
        "frontend_dist": str(
            FRONTEND_DIST
        ),
        "frontend_dist_exists": FRONTEND_DIST.exists(),
        "assets_dir": str(
            ASSETS_DIR
        ),
        "assets_exists": ASSETS_DIR.exists(),
        "index_exists": (
            FRONTEND_DIST / "index.html"
        ).exists(),
        "assets": (
            [
                item.name
                for item in ASSETS_DIR.iterdir()
                if item.is_file()
            ]
            if ASSETS_DIR.exists()
            else []
        ),
    }


@app.get("/{full_path:path}")
def serve_frontend(
    full_path: str,
):
    if full_path.startswith("api/"):
        raise HTTPException(
            status_code=404,
            detail="API endpoint not found",
        )

    if full_path.startswith("assets/"):
        raise HTTPException(
            status_code=404,
            detail="Frontend asset not found",
        )

    if full_path:
        requested_file = (
            FRONTEND_DIST
            / full_path
        )

        if (
            requested_file.exists()
            and requested_file.is_file()
        ):
            return FileResponse(
                requested_file
            )

    index_file = (
        FRONTEND_DIST
        / "index.html"
    )

    if index_file.exists():
        return FileResponse(
            index_file
        )

    raise HTTPException(
        status_code=500,
        detail={
            "message": "Frontend build not found",
            "frontend_dist": str(
                FRONTEND_DIST
            ),
        },
    )
