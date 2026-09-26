from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from typing import Any


PBKDF2_ITERATIONS = (
    200_000
)

#
# Повторный запрос авторизации
# с одного устройства после
# 1 часа бездействия.
#
INACTIVITY_TIMEOUT = (
    timedelta(
        hours=1
    )
)


def hash_password(
    password: str,
    salt: str | None = None,
) -> str:
    if salt is None:
        salt = (
            secrets
            .token_hex(
                16
            )
        )

    digest = (
        hashlib
        .pbkdf2_hmac(
            "sha256",

            password
            .encode(
                "utf-8"
            ),

            salt
            .encode(
                "utf-8"
            ),

            PBKDF2_ITERATIONS,
        )
        .hex()
    )

    return (
        f"{salt}${digest}"
    )


def verify_password(
    password: str,
    stored: str,
) -> bool:
    parts = (
        stored
        .split(
            "$",
            1,
        )
    )

    if (
        len(parts)
        != 2
    ):
        return False

    salt = (
        parts[0]
    )

    expected = (
        parts[1]
    )

    actual = (
        hash_password(
            password,
            salt,
        )
        .split(
            "$",
            1,
        )[1]
    )

    return (
        hmac
        .compare_digest(
            expected,
            actual
        )
    )


@dataclass(slots=True)
class AuthUser:
    id: int
    login: str
    full_name: str


@dataclass(slots=True)
class AuthService:
    """
    п.6 плана v1.2: регистрация
    при первом запуске и
    авторизация.

    Логин+пароль, PIN на устройстве
    или биометрия (WebAuthn platform:
    отпечаток/Face ID). Сессия
    устройства истекает после
    1 часа бездействия.
    """

    repository: Any

    def has_users(
        self,
    ) -> bool:
        return (
            self
            .repository
            .count_users()
            > 0
        )

    def register(
        self,
        full_name: str,
        phone: str,
        email: str,
        birth_date: str,
        login: str,
        password: str,
        device_id: str,
    ) -> tuple[
        AuthUser,
        str,
    ]:
        existing = (
            self
            .repository
            .get_user_by_login(
                login
            )
        )

        if (
            existing
            is not None
        ):
            raise ValueError(
                "Логин уже занят"
            )

        user = (
            self
            .repository
            .create_user(
                full_name=(
                    full_name
                    .strip()
                ),

                phone=(
                    phone
                    .strip()
                ),

                email=(
                    email
                    .strip()
                ),

                birth_date=(
                    birth_date
                    .strip()
                ),

                login=(
                    login
                    .strip()
                ),

                password_hash=(
                    hash_password(
                        password
                    )
                ),
            )
        )

        token = (
            self
            ._issue_session(
                user_id=(
                    user.id
                ),

                device_id=(
                    device_id
                ),
            )
        )

        return (
            AuthUser(
                id=(
                    user.id
                ),

                login=(
                    user.login
                ),

                full_name=(
                    user
                    .full_name
                ),
            ),

            token,
        )

    def login(
        self,
        login: str,
        password: str,
        device_id: str,
    ) -> tuple[
        AuthUser,
        str,
    ]:
        user = (
            self
            .repository
            .get_user_by_login(
                login
                .strip()
            )
        )

        if (
            user
            is None
        ):
            raise ValueError(
                "Неверный логин "
                "или пароль"
            )

        if (
            not verify_password(
                password,

                user
                .password_hash,
            )
        ):
            raise ValueError(
                "Неверный логин "
                "или пароль"
            )

        token = (
            self
            ._issue_session(
                user_id=(
                    user.id
                ),

                device_id=(
                    device_id
                ),
            )
        )

        return (
            AuthUser(
                id=(
                    user.id
                ),

                login=(
                    user.login
                ),

                full_name=(
                    user
                    .full_name
                ),
            ),

            token,
        )

    def set_pin(
        self,
        token: str,
        device_id: str,
        pin: str,
    ) -> None:
        session = (
            self
            ._require_session(
                token
            )
        )

        if (
            not pin
            .isdigit()
            or not (
                4
                <= len(
                    pin
                )
                <= 8
            )
        ):
            raise ValueError(
                "PIN: 4-8 цифр"
            )

        self.repository.upsert_device(
            device_id=(
                device_id
            ),

            user_id=(
                session
                .user_id
            ),
        )

        self.repository.set_device_pin(
            device_id=(
                device_id
            ),

            pin_hash=(
                hash_password(
                    pin
                )
            ),
        )

    def verify_pin(
        self,
        device_id: str,
        pin: str,
    ) -> tuple[
        AuthUser,
        str,
    ]:
        device = (
            self
            .repository
            .get_device(
                device_id
            )
        )

        if (
            device
            is None
            or (
                device
                .pin_hash
                is None
            )
        ):
            raise ValueError(
                "PIN на этом "
                "устройстве "
                "не задан"
            )

        if (
            not verify_password(
                pin,

                device
                .pin_hash,
            )
        ):
            raise ValueError(
                "Неверный PIN"
            )

        user = (
            self
            .repository
            .get_user_by_id(
                device
                .user_id
            )
        )

        if (
            user
            is None
        ):
            raise ValueError(
                "Пользователь "
                "не найден"
            )

        token = (
            self
            ._issue_session(
                user_id=(
                    user.id
                ),

                device_id=(
                    device_id
                ),
            )
        )

        return (
            AuthUser(
                id=(
                    user.id
                ),

                login=(
                    user.login
                ),

                full_name=(
                    user
                    .full_name
                ),
            ),

            token,
        )

    def device_has_pin(
        self,
        device_id: str,
    ) -> bool:
        device = (
            self
            .repository
            .get_device(
                device_id
            )
        )

        return (
            device
            is not None
            and (
                device
                .pin_hash
                is not None
            )
        )

    def set_biometric(
        self,
        token: str,
        device_id: str,
        credential_id: str,
    ) -> None:
        session = (
            self
            ._require_session(
                token
            )
        )

        self.repository.upsert_device(
            device_id=(
                device_id
            ),

            user_id=(
                session
                .user_id
            ),
        )

        self.repository.set_device_biometric(
            device_id=(
                device_id
            ),

            credential_id=(
                credential_id
            ),
        )

    def disable_biometric(
        self,
        token: str,
        device_id: str,
    ) -> None:
        self._require_session(
            token
        )

        self.repository.set_device_biometric(
            device_id=(
                device_id
            ),

            credential_id=(
                None
            ),
        )

    def device_has_biometric(
        self,
        device_id: str,
    ) -> bool:
        device = (
            self
            .repository
            .get_device(
                device_id
            )
        )

        return (
            device
            is not None
            and (
                device
                .biometric_credential_id
                is not None
            )
        )

    def verify_biometric(
        self,
        device_id: str,
        credential_id: str,
    ) -> tuple[
        AuthUser,
        str,
    ]:
        device = (
            self
            .repository
            .get_device(
                device_id
            )
        )

        if (
            device
            is None
            or (
                device
                .biometric_credential_id
                is None
            )
        ):
            raise ValueError(
                "Биометрия на этом "
                "устройстве "
                "не настроена"
            )

        if (
            not hmac
            .compare_digest(
                device
                .biometric_credential_id,

                credential_id,
            )
        ):
            raise ValueError(
                "Биометрия "
                "не распознана"
            )

        user = (
            self
            .repository
            .get_user_by_id(
                device
                .user_id
            )
        )

        if (
            user
            is None
        ):
            raise ValueError(
                "Пользователь "
                "не найден"
            )

        token = (
            self
            ._issue_session(
                user_id=(
                    user.id
                ),

                device_id=(
                    device_id
                ),
            )
        )

        return (
            AuthUser(
                id=(
                    user.id
                ),

                login=(
                    user.login
                ),

                full_name=(
                    user
                    .full_name
                ),
            ),

            token,
        )

    def get_user_by_token(
        self,
        token: str,
    ) -> (
        AuthUser | None
    ):
        session = (
            self
            .repository
            .get_session(
                token
            )
        )

        if (
            session
            is None
        ):
            return None

        last_activity = (
            self
            ._parse_ts(
                session
                .last_activity
            )
        )

        now = (
            datetime
            .now(
                timezone.utc
            )
        )

        if (
            now
            - last_activity
            > INACTIVITY_TIMEOUT
        ):
            #
            # Больше часа
            # бездействия —
            # авторизация
            # запрашивается
            # заново.
            #
            self.repository.delete_session(
                token
            )

            return None

        self.repository.touch_session(
            token=(
                token
            ),

            last_activity=(
                now
                .isoformat()
            ),
        )

        user = (
            self
            .repository
            .get_user_by_id(
                session
                .user_id
            )
        )

        if (
            user
            is None
        ):
            return None

        return (
            AuthUser(
                id=(
                    user.id
                ),

                login=(
                    user.login
                ),

                full_name=(
                    user
                    .full_name
                ),
            )
        )

    def logout(
        self,
        token: str,
    ) -> None:
        self.repository.delete_session(
            token
        )

    def _issue_session(
        self,
        user_id: int,
        device_id: str,
    ) -> str:
        token = (
            secrets
            .token_urlsafe(
                32
            )
        )

        self.repository.upsert_device(
            device_id=(
                device_id
            ),

            user_id=(
                user_id
            ),
        )

        self.repository.create_session(
            token=(
                token
            ),

            user_id=(
                user_id
            ),

            device_id=(
                device_id
            ),

            created_at=(
                datetime
                .now(
                    timezone.utc
                )
                .isoformat()
            ),
        )

        return token

    def _require_session(
        self,
        token: str,
    ):
        user = (
            self
            .get_user_by_token(
                token
            )
        )

        if (
            user
            is None
        ):
            raise ValueError(
                "Требуется "
                "авторизация"
            )

        session = (
            self
            .repository
            .get_session(
                token
            )
        )

        assert (
            session
            is not None
        )

        return session

    @staticmethod
    def _parse_ts(
        value: str,
    ) -> datetime:
        try:
            parsed = (
                datetime
                .fromisoformat(
                    value
                )
            )

            if (
                parsed.tzinfo
                is None
            ):
                parsed = (
                    parsed
                    .replace(
                        tzinfo=(
                            timezone
                            .utc
                        )
                    )
                )

            return parsed

        except ValueError:
            return (
                datetime
                .now(
                    timezone.utc
                )
            )
