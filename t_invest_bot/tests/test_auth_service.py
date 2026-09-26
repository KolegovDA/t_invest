from __future__ import annotations

from pathlib import Path

from application.auth_service import (
    AuthService,
    INACTIVITY_TIMEOUT,
    hash_password,
    verify_password,
)

from infrastructure.sqlite.user_repository import (
    SQLiteUserRepository,
)


def make_service(
    tmp_path: Path,
) -> AuthService:
    repository = (
        SQLiteUserRepository(
            db_path=str(
                tmp_path
                / "auth.db"
            ),
        )
    )

    return (
        AuthService(
            repository=(
                repository
            ),
        )
    )


def test_password_hash_roundtrip() -> None:
    stored = (
        hash_password(
            "secret-123"
        )
    )

    assert (
        verify_password(
            "secret-123",

            stored,
        )
        is True
    )

    assert (
        verify_password(
            "wrong",

            stored,
        )
        is False
    )


def test_register_and_login(
    tmp_path: Path,
) -> None:
    service = (
        make_service(
            tmp_path
        )
    )

    assert (
        service
        .has_users()
        is False
    )

    user, token = (
        service
        .register(
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

            password=(
                "pass-1"
            ),

            device_id=(
                "device-1"
            ),
        )
    )

    assert (
        user.login
        == "ivan"
    )

    assert (
        service
        .has_users()
        is True
    )

    me = (
        service
        .get_user_by_token(
            token
        )
    )

    assert (
        me
        is not None
    )

    assert (
        me.id
        == (
            user.id
        )
    )

    _, token2 = (
        service
        .login(
            login="ivan",

            password=(
                "pass-1"
            ),

            device_id=(
                "device-2"
            ),
        )
    )

    assert (
        service
        .get_user_by_token(
            token2
        )
        is not None
    )


def test_duplicate_login_rejected(
    tmp_path: Path,
) -> None:
    service = (
        make_service(
            tmp_path
        )
    )

    service.register(
        full_name="A",
        phone="1",
        email="a@a",
        birth_date="2000-01-01",
        login="user-a",
        password="p",
        device_id="d",
    )

    try:
        service.register(
            full_name="B",
            phone="2",
            email="b@b",
            birth_date="2000-01-01",
            login="user-a",
            password="p",
            device_id="d",
        )

        raise (
            AssertionError(
                "должен был упасть"
            )
        )

    except ValueError:
        pass


def test_wrong_password_rejected(
    tmp_path: Path,
) -> None:
    service = (
        make_service(
            tmp_path
        )
    )

    service.register(
        full_name="A",
        phone="1",
        email="a@a",
        birth_date="2000-01-01",
        login="user-a",
        password="p",
        device_id="d",
    )

    try:
        service.login(
            login="user-a",
            password="wrong",
            device_id="d",
        )

        raise (
            AssertionError(
                "должен был упасть"
            )
        )

    except ValueError:
        pass


def test_pin_flow(
    tmp_path: Path,
) -> None:
    service = (
        make_service(
            tmp_path
        )
    )

    _, token = (
        service
        .register(
            full_name="A",
            phone="1",
            email="a@a",
            birth_date="2000-01-01",
            login="user-a",
            password="p",
            device_id=(
                "device-1"
            ),
        )
    )

    assert (
        service
        .device_has_pin(
            "device-1"
        )
        is False
    )

    service.set_pin(
        token=(
            token
        ),

        device_id=(
            "device-1"
        ),

        pin="1234",
    )

    assert (
        service
        .device_has_pin(
            "device-1"
        )
        is True
    )

    user, token2 = (
        service
        .verify_pin(
            device_id=(
                "device-1"
            ),

            pin="1234",
        )
    )

    assert (
        user.login
        == "user-a"
    )

    try:
        service.verify_pin(
            device_id=(
                "device-1"
            ),

            pin="0000",
        )

        raise (
            AssertionError(
                "должен был упасть"
            )
        )

    except ValueError:
        pass

    try:
        service.set_pin(
            token=(
                token2
            ),

            device_id=(
                "device-1"
            ),

            pin="abc",
        )

        raise (
            AssertionError(
                "недопустимый PIN "
                "принят"
            )
        )

    except ValueError:
        pass


def test_biometric_flow(
    tmp_path: Path,
) -> None:
    service = (
        make_service(
            tmp_path
        )
    )

    _, token = (
        service
        .register(
            full_name="A",
            phone="1",
            email="a@a",
            birth_date="2000-01-01",
            login="user-a",
            password="p",
            device_id=(
                "device-1"
            ),
        )
    )

    assert (
        service
        .device_has_biometric(
            "device-1"
        )
        is False
    )

    service.set_biometric(
        token=(
            token
        ),

        device_id=(
            "device-1"
        ),

        credential_id=(
            "cred-abc"
        ),
    )

    assert (
        service
        .device_has_biometric(
            "device-1"
        )
        is True
    )

    user, _ = (
        service
        .verify_biometric(
            device_id=(
                "device-1"
            ),

            credential_id=(
                "cred-abc"
            ),
        )
    )

    assert (
        user.login
        == "user-a"
    )

    try:
        service.verify_biometric(
            device_id=(
                "device-1"
            ),

            credential_id=(
                "cred-xyz"
            ),
        )

        raise (
            AssertionError(
                "должен был упасть"
            )
        )

    except ValueError:
        pass

    service.disable_biometric(
        token=(
            token
        ),

        device_id=(
            "device-1"
        ),
    )

    assert (
        service
        .device_has_biometric(
            "device-1"
        )
        is False
    )


def test_session_expires_after_inactivity(
    tmp_path: Path,
) -> None:
    service = (
        make_service(
            tmp_path
        )
    )

    _, token = (
        service
        .register(
            full_name="A",
            phone="1",
            email="a@a",
            birth_date="2000-01-01",
            login="user-a",
            password="p",
            device_id="d",
        )
    )

    assert (
        INACTIVITY_TIMEOUT
        .total_seconds()
        == 3600
    )

    #
    # Симулируем час
    # бездействия: сдвигаем
    # last_activity назад.
    #
    service.repository.touch_session(
        token=(
            token
        ),

        last_activity=(
            "2020-01-01T00:00:00"
            "+00:00"
        ),
    )

    assert (
        service
        .get_user_by_token(
            token
        )
        is None
    )


def test_logout(
    tmp_path: Path,
) -> None:
    service = (
        make_service(
            tmp_path
        )
    )

    _, token = (
        service
        .register(
            full_name="A",
            phone="1",
            email="a@a",
            birth_date="2000-01-01",
            login="user-a",
            password="p",
            device_id="d",
        )
    )

    service.logout(
        token
    )

    assert (
        service
        .get_user_by_token(
            token
        )
        is None
    )
