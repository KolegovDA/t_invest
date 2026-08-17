from __future__ import annotations

import base64
import ctypes
import sys

from ctypes import (
    POINTER,
    Structure,
    byref,
    c_char,
    c_void_p,
)
from ctypes.wintypes import (
    BOOL,
    DWORD,
)


class DATA_BLOB(
    Structure
):
    _fields_ = [
        (
            "cbData",
            DWORD,
        ),
        (
            "pbData",
            POINTER(c_char),
        ),
    ]


class DPAPISecretProtector:
    """
    Защита токенов через
    Windows Data Protection API.

    Токен может расшифровать
    только тот же Windows user,
    под которым запущено приложение.
    """

    def __init__(
        self,
    ) -> None:
        if sys.platform != "win32":
            raise RuntimeError(
                "DPAPISecretProtector "
                "requires Windows"
            )

        self.crypt32 = (
            ctypes.windll.crypt32
        )

        self.kernel32 = (
            ctypes.windll.kernel32
        )

    def protect(
        self,
        value: str,
    ) -> str:
        if not value:
            raise ValueError(
                "Secret is empty"
            )

        raw = value.encode(
            "utf-8"
        )

        input_buffer = (
            ctypes.create_string_buffer(
                raw
            )
        )

        input_blob = DATA_BLOB(
            cbData=len(raw),

            pbData=ctypes.cast(
                input_buffer,
                POINTER(c_char),
            ),
        )

        output_blob = DATA_BLOB()

        result = (
            self.crypt32
            .CryptProtectData(
                byref(input_blob),
                "ESM Trade System",
                None,
                None,
                None,
                0,
                byref(output_blob),
            )
        )

        if not result:
            raise ctypes.WinError()

        try:
            encrypted = (
                ctypes.string_at(
                    output_blob.pbData,
                    output_blob.cbData,
                )
            )

            return (
                base64.b64encode(
                    encrypted
                )
                .decode(
                    "ascii"
                )
            )

        finally:
            if output_blob.pbData:
                self.kernel32.LocalFree(
                    output_blob.pbData
                )

    def unprotect(
        self,
        value: str,
    ) -> str:
        if not value:
            raise ValueError(
                "Protected secret is empty"
            )

        encrypted = (
            base64.b64decode(
                value.encode(
                    "ascii"
                )
            )
        )

        input_buffer = (
            ctypes.create_string_buffer(
                encrypted
            )
        )

        input_blob = DATA_BLOB(
            cbData=len(
                encrypted
            ),

            pbData=ctypes.cast(
                input_buffer,
                POINTER(c_char),
            ),
        )

        output_blob = DATA_BLOB()

        result = (
            self.crypt32
            .CryptUnprotectData(
                byref(input_blob),
                None,
                None,
                None,
                None,
                0,
                byref(output_blob),
            )
        )

        if not result:
            raise ctypes.WinError()

        try:
            raw = (
                ctypes.string_at(
                    output_blob.pbData,
                    output_blob.cbData,
                )
            )

            return raw.decode(
                "utf-8"
            )

        finally:
            if output_blob.pbData:
                self.kernel32.LocalFree(
                    output_blob.pbData
                )
