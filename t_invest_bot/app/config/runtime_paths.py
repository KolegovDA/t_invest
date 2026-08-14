from __future__ import annotations

import sys
from pathlib import Path


def get_application_root() -> Path:
    if getattr(
        sys,
        "frozen",
        False,
    ):
        return (
            Path(
                sys.executable
            )
            .resolve()
            .parent
        )

    return (
        Path(__file__)
        .resolve()
        .parents[2]
    )


def get_data_directory() -> Path:
    directory = (
        get_application_root()
        / "data"
    )

    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    return directory


def get_database_path() -> Path:
    return (
        get_data_directory()
        / "tinvest.db"
    )
