from __future__ import annotations

import base64
import json

from dataclasses import dataclass
from pathlib import Path

from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PublicFormat,
)
from py_vapid import Vapid01


VAPID_FILE_NAME = (
    "webpush_vapid.json"
)


@dataclass(slots=True)
class VapidKeyPair:
    # Публичный ключ (base64url,
    # 65 байт несжатой точки P-256) —
    # отдаётся браузеру как
    # applicationServerKey.
    public_key: str

    # Приватный ключ PEM — только
    # на сервере, подписывает
    # Web Push запросы.
    private_pem: str


def load_or_create_vapid_keys(
    data_directory: Path,
) -> VapidKeyPair:
    file_path = (
        data_directory
        / VAPID_FILE_NAME
    )

    if (
        file_path
        .exists()
    ):
        payload = (
            json
            .loads(
                file_path
                .read_text(
                    encoding=(
                        "utf-8"
                    ),
                )
            )
        )

        return VapidKeyPair(
            public_key=(
                payload[
                    "public_key"
                ]
            ),

            private_pem=(
                payload[
                    "private_pem"
                ]
            ),
        )

    vapid = Vapid01()

    vapid.generate_keys()

    raw_public = (
        vapid
        .public_key
        .public_bytes(
            Encoding.X962,

            PublicFormat
            .UncompressedPoint,
        )
    )

    key_pair = (
        VapidKeyPair(
            public_key=(
                base64
                .urlsafe_b64encode(
                    raw_public
                )
                .rstrip(
                    b"="
                )
                .decode(
                    "ascii"
                )
            ),

            private_pem=(
                vapid
                .private_pem()
                .decode(
                    "utf-8"
                )
            ),
        )
    )

    (
        file_path
        .write_text(
            json.dumps(
                {
                    "public_key": (
                        key_pair
                        .public_key
                    ),

                    "private_pem": (
                        key_pair
                        .private_pem
                    ),
                }
            ),

            encoding="utf-8",
        )
    )

    return key_pair
