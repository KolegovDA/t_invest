from decimal import Decimal
from pathlib import Path
import sqlite3
import sys

from config.runtime_paths import (
    get_database_path,
    migrate_legacy_database,
)
from infrastructure.security.field_encryption import (
    DPAPIFieldCipher,
    ENCRYPTED_PREFIX,
)
from infrastructure.sqlite.user_repository import (
    SQLiteUserRepository,
)


WINDOWS = (
    sys.platform
    == "win32"
)


class FakeProtector:
    def protect(
        self,
        value: str,
    ) -> str:
        return (
            "FAKE"
            + value[
                ::-1
            ]
        )

    def unprotect(
        self,
        value: str,
    ) -> str:
        return (
            value[
                4:
            ][
                ::-1
            ]
        )


def create_cipher() -> (
    DPAPIFieldCipher
):
    return (
        DPAPIFieldCipher(
            protector=(
                FakeProtector()
            ),
        )
    )


def test_field_cipher_roundtrip() -> None:
    cipher = (
        create_cipher()
    )

    original = (
        "salt$abcdef123456"
    )

    encrypted = (
        cipher
        .encrypt(
            original
        )
    )

    assert (
        encrypted
        .startswith(
            ENCRYPTED_PREFIX
        )
    )

    assert (
        encrypted
        != original
    )

    assert (
        cipher
        .decrypt(
            encrypted
        )
        == original
    )


def test_field_cipher_passes_plain_values() -> None:
    cipher = (
        create_cipher()
    )

    legacy = (
        "legacy-hash"
    )

    assert (
        cipher
        .decrypt(
            legacy
        )
        == legacy
    )

    assert (
        cipher
        .decrypt(
            None
        )
        is None
    )

    assert (
        cipher
        .encrypt(
            None
        )
        is None
    )

    assert (
        cipher
        .encrypt(
            ""
        )
        == ""
    )


def test_field_cipher_does_not_double_encrypt() -> None:
    cipher = (
        create_cipher()
    )

    once = (
        cipher
        .encrypt(
            "value"
        )
    )

    twice = (
        cipher
        .encrypt(
            once
        )
    )

    assert (
        once
        == twice
    )


def test_user_repository_stores_encrypted_password(
    tmp_path: Path,
) -> None:
    repository = (
        SQLiteUserRepository(
            db_path=str(
                tmp_path
                / "users.db"
            ),

            field_cipher=(
                create_cipher()
            ),
        )
    )

    repository.create_user(
        full_name=(
            "Иван Иванов"
        ),

        phone=(
            "+79001234567"
        ),

        email=(
            "ivan@example.com"
        ),

        birth_date=(
            "1990-01-01"
        ),

        login="ivan",

        password_hash=(
            "salt$hash"
        ),
    )

    with sqlite3.connect(
        str(
            tmp_path
            / "users.db"
        )
    ) as connection:
        row = (
            connection
            .execute(
                "SELECT password_hash FROM users WHERE login = ?",
                (
                    "ivan",
                ),
            )
            .fetchone()
        )

    stored = (
        row[
            0
        ]
    )

    assert (
        stored
        .startswith(
            ENCRYPTED_PREFIX
        )
    )

    assert (
        stored
        != "salt$hash"
    )

    user = (
        repository
        .get_user_by_login(
            "ivan"
        )
    )

    assert (
        user
        is not None
    )

    assert (
        user
        .password_hash
        == "salt$hash"
    )


def test_user_repository_reads_legacy_plaintext(
    tmp_path: Path,
) -> None:
    db_path = (
        tmp_path
        / "users.db"
    )

    with sqlite3.connect(
        str(
            db_path
        )
    ) as connection:
        connection.execute(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY
                    AUTOINCREMENT,
                full_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                email TEXT NOT NULL,
                birth_date TEXT NOT NULL,
                login TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        connection.execute(
            """
            INSERT INTO users (
                full_name,
                phone,
                email,
                birth_date,
                login,
                password_hash
            )
            VALUES (
                'Пётр Петров',
                '+79005553535',
                'petr@example.com',
                '1980-01-01',
                'petr',
                'plain$hash'
            )
            """
        )

    repository = (
        SQLiteUserRepository(
            db_path=str(
                db_path
            ),

            field_cipher=(
                create_cipher()
            ),
        )
    )

    user = (
        repository
        .get_user_by_login(
            "petr"
        )
    )

    assert (
        user
        is not None
    )

    assert (
        user
        .password_hash
        == "plain$hash"
    )

    with sqlite3.connect(
        str(
            db_path
        )
    ) as connection:
        row = (
            connection
            .execute(
                "SELECT password_hash FROM users WHERE login = ?",
                (
                    "petr",
                ),
            )
            .fetchone()
        )

    assert (
        row[
            0
        ]
        .startswith(
            ENCRYPTED_PREFIX
        )
    )


def test_head_api_key_encrypted(
    tmp_path: Path,
) -> None:
    repository = (
        SQLiteUserRepository(
            db_path=str(
                tmp_path
                / "users.db"
            ),

            field_cipher=(
                create_cipher()
            ),
        )
    )

    user = (
        repository
        .create_user(
            full_name=(
                "Сидор Сидоров"
            ),

            phone=(
                "+79009998877"
            ),

            email=(
                "sidor@example.com"
            ),

            birth_date=(
                "1970-01-01"
            ),

            login="sidor",

            password_hash=(
                "salt$hash2"
            ),
        )
    )

    repository.set_user_head_api_key(
        user_id=(
            user.id
        ),

        api_key=(
            "secret-api-key"
        ),
    )

    with sqlite3.connect(
        str(
            tmp_path
            / "users.db"
        )
    ) as connection:
        row = (
            connection
            .execute(
                "SELECT head_api_key FROM users WHERE id = ?",
                (
                    user.id,
                ),
            )
            .fetchone()
        )

    assert (
        row[
            0
        ]
        .startswith(
            ENCRYPTED_PREFIX
        )
    )

    assert (
        repository
        .get_user_head_api_key(
            user.id
        )
        == "secret-api-key"
    )

    reloaded = (
        repository
        .get_user_by_id(
            user.id
        )
    )

    assert (
        reloaded
        .head_api_key
        == "secret-api-key"
    )


def test_migrate_legacy_database_moves_file(
    tmp_path: Path,
    monkeypatch,
) -> None:
    legacy_dir = (
        tmp_path
        / "app"
        / "data"
    )

    legacy_dir.mkdir(
        parents=True,
    )

    legacy_db = (
        legacy_dir
        / "tinvest.db"
    )

    connection = (
        sqlite3
        .connect(
            str(
                legacy_db
            )
        )
    )

    try:
        connection.execute(
            """
            CREATE TABLE demo (
                id INTEGER PRIMARY KEY,
                value TEXT
            )
            """
        )

        connection.execute(
            "INSERT INTO demo (value) VALUES ('data')"
        )

        connection.commit()

    finally:
        connection.close()

    monkeypatch.setattr(
        "config.runtime_paths.get_application_root",

        lambda: (
            tmp_path
            / "app"
        ),
    )

    new_db = (
        tmp_path
        / "new"
        / "tinvest.db"
    )

    moved_from = (
        migrate_legacy_database(
            new_db
        )
    )

    assert (
        moved_from
        == legacy_db
    )

    assert (
        new_db
        .exists()
    )

    assert (
        not legacy_db
        .exists()
    )

    verify = (
        sqlite3
        .connect(
            str(
                new_db
            )
        )
    )

    try:
        row = (
            verify
            .execute(
                "SELECT value FROM demo"
            )
            .fetchone()
        )

    finally:
        verify.close()

    assert (
        row[
            0
        ]
        == "data"
    )


def test_migrate_legacy_database_skips_when_new_exists(
    tmp_path: Path,
    monkeypatch,
) -> None:
    legacy_dir = (
        tmp_path
        / "app"
        / "data"
    )

    legacy_dir.mkdir(
        parents=True,
    )

    legacy_db = (
        legacy_dir
        / "tinvest.db"
    )

    legacy_db.write_text(
        "legacy"
    )

    monkeypatch.setattr(
        "config.runtime_paths.get_application_root",

        lambda: (
            tmp_path
            / "app"
        ),
    )

    new_db = (
        tmp_path
        / "new"
        / "tinvest.db"
    )

    new_db.parent.mkdir(
        parents=True,
    )

    new_db.write_text(
        "new"
    )

    result = (
        migrate_legacy_database(
            new_db
        )
    )

    assert (
        result
        is None
    )

    assert (
        new_db
        .read_text()
        == "new"
    )

    assert (
        legacy_db
        .exists()
    )


def test_get_database_path_uses_env_override(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "ESM_DATA_DIR",

        str(
            tmp_path
        ),
    )

    db_path = (
        get_database_path()
    )

    assert (
        db_path
        == (
            tmp_path
            / "tinvest.db"
        )
    )

    assert (
        db_path
        .parent
        .exists()
    )
