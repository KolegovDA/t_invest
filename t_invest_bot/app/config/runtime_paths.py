from __future__ import annotations

import os
import shutil
import sqlite3
import sys
from pathlib import Path


FILE_ATTRIBUTE_HIDDEN = 0x2
FILE_ATTRIBUTE_SYSTEM = 0x4


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


def _env_data_directory() -> Path | None:
    value = (
        os.getenv(
            "ESM_DATA_DIR"
        )
    )

    if not value:
        return None

    return (
        Path(
            value
        )
        .resolve()
    )


def _program_data_directory() -> Path:
    program_data = (
        os.getenv(
            "PROGRAMDATA"
        )
        or (
            "C:\\ProgramData"
        )
    )

    return (
        Path(
            program_data
        )
        / "ESMTradeSystem"
    )


def _make_hidden(
    path: Path,
) -> None:
    if (
        sys.platform
        != "win32"
    ):
        return

    try:
        import ctypes

        ctypes\
            .windll\
            .kernel32\
            .SetFileAttributesW(
                str(
                    path
                ),

                (
                    FILE_ATTRIBUTE_HIDDEN
                    | FILE_ATTRIBUTE_SYSTEM
                ),
            )

    except Exception:
        pass


def _uses_program_data() -> bool:
    if (
        _env_data_directory()
        is not None
    ):
        return False

    return (
        getattr(
            sys,
            "frozen",
            False,
        )
    )


def _verify_sqlite(
    db_path: Path,
) -> bool:
    try:
        connection = (
            sqlite3
            .connect(
                str(
                    db_path
                )
            )
        )

        try:
            row = (
                connection
                .execute(
                    "PRAGMA integrity_check"
                )
                .fetchone()
            )

            return (
                row
                is not None
                and str(
                    row[
                        0
                    ]
                )
                .lower()
                == "ok"
            )

        finally:
            connection.close()

    except Exception:
        return False


def migrate_legacy_database(
    new_db_path: Path,
) -> (
    Path | None
):
    """
    v1.3 (п. 4): перенос
    существующей БД из папки
    запуска в новое место.

    Копируем, проверяем
    целостность копии и только
    потом удаляем старый файл.
    """

    legacy_path = (
        get_application_root()
        / "data"
        / "tinvest.db"
    )

    if (
        new_db_path
        == legacy_path
    ):
        return None

    if (
        new_db_path
        .exists()
    ):
        return None

    if (
        not legacy_path
        .exists()
    ):
        return None

    new_db_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        legacy_path,

        new_db_path,
    )

    if (
        not _verify_sqlite(
            new_db_path
        )
    ):
        new_db_path.unlink(
            missing_ok=True,
        )

        raise RuntimeError(
            "Legacy database "
            "migration failed: "
            "integrity check "
            "did not pass"
        )

    try:
        legacy_path.unlink()

    except OSError:
        try:
            legacy_path.rename(
                legacy_path
                .with_suffix(
                    ".db.migrated"
                )
            )

        except OSError:
            print(
                "LEGACY DATABASE "
                "CLEANUP FAILED: "
                "old file left "
                "in place",

                str(
                    legacy_path
                ),
            )

    legacy_dir = (
        legacy_path
        .parent
    )

    try:
        if (
            not any(
                legacy_dir
                .iterdir()
            )
        ):
            legacy_dir.rmdir()
    except OSError:
        pass

    return legacy_path


def get_data_directory() -> Path:
    env_directory = (
        _env_data_directory()
    )

    if (
        env_directory
        is not None
    ):
        env_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        return (
            env_directory
        )

    if (
        _uses_program_data()
    ):
        root = (
            _program_data_directory()
        )

        directory = (
            root / "data"
        )

        root.mkdir(
            parents=True,
            exist_ok=True,
        )

        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        _make_hidden(
            root
        )

        return (
            directory
        )

    directory = (
        get_application_root()
        / "data"
    )

    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    return (
        directory
    )


def get_database_path() -> Path:
    db_path = (
        get_data_directory()
        / "tinvest.db"
    )

    if (
        _uses_program_data()
    ):
        try:
            migrate_legacy_database(
                db_path
            )

        except Exception as error:
            print(
                "DATABASE MIGRATION ERROR:",
                repr(
                    error
                ),
            )

    return db_path
