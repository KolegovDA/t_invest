from __future__ import annotations

import sys
from typing import Any


ENCRYPTED_PREFIX = (
    "dpapi:"
)


class _PassthroughFieldCipher:
    def encrypt(
        self,
        value: (
            str | None
        ),
    ) -> (
        str | None
    ):
        return value

    def decrypt(
        self,
        value: (
            str | None
        ),
    ) -> (
        str | None
    ):
        return value


class DPAPIFieldCipher:
    """
    v1.3 (п. 4): прозрачное
    шифрование чувствительных
    полей БД через DPAPI.

    Зашифрованные значения
    хранятся с префиксом
    «dpapi:».

    Значения без префикса
    (legacy, записанные до
    шифрования) читаются
    как есть.

    На не-Windows системах
    работает сквозная
    передача без шифрования.
    """

    def __init__(
        self,
        protector: Any = None,
    ) -> None:
        self._protector = (
            protector
        )

    def _get_protector(
        self,
    ) -> Any:
        if (
            self._protector
            is not None
        ):
            return (
                self
                ._protector
            )

        if (
            sys.platform
            != "win32"
        ):
            return None

        from infrastructure.security.dpapi_secret_protector import (
            DPAPISecretProtector,
        )

        self._protector = (
            DPAPISecretProtector()
        )

        return (
            self
            ._protector
        )

    def is_encrypted(
        self,
        value: (
            str | None
        ),
    ) -> bool:
        return (
            value
            is not None
            and value
            .startswith(
                ENCRYPTED_PREFIX
            )
        )

    def encrypt(
        self,
        value: (
            str | None
        ),
    ) -> (
        str | None
    ):
        if not value:
            return value

        if (
            self
            .is_encrypted(
                value
            )
        ):
            return value

        protector = (
            self
            ._get_protector()
        )

        if (
            protector
            is None
        ):
            return value

        protected = (
            protector
            .protect(
                value
            )
        )

        return (
            ENCRYPTED_PREFIX
            + protected
        )

    def decrypt(
        self,
        value: (
            str | None
        ),
    ) -> (
        str | None
    ):
        if not value:
            return value

        if not (
            self
            .is_encrypted(
                value
            )
        ):
            return value

        protector = (
            self
            ._get_protector()
        )

        if (
            protector
            is None
        ):
            return value

        return (
            protector
            .unprotect(
                value[
                    len(
                        ENCRYPTED_PREFIX
                    ):
                ]
            )
        )


def make_field_cipher() -> Any:
    if (
        sys.platform
        != "win32"
    ):
        return (
            _PassthroughFieldCipher()
        )

    return (
        DPAPIFieldCipher()
    )
