from __future__ import annotations

import json

from dataclasses import dataclass

from datetime import (
    datetime,
    timezone,
)

from typing import Protocol

from uuid import uuid4

from application.trading_account_service import TradingAccountService
from domain.trading_state import TradingSessionState
from domain.platform_connection import (
    PlatformConnection,
)
from domain.trading_account import (
    BrokerType,
    TradingAccountMode,
)
from infrastructure.sqlite.platform_connection_repository import (
    PlatformConnectionRepository,
)


class SecretProtector(
    Protocol
):
    def protect(
        self,
        value: str,
    ) -> str:
        ...

    def unprotect(
        self,
        value: str,
    ) -> str:
        ...


@dataclass(slots=True)
class PlatformConnectionService:
    #
    # Подключение ПЛАТФОРМЫ
    # (брокера): только ключи
    # доступа, без выбора счёта.
    # Счета добавляются отдельно
    # на вкладке «Счета» и берут
    # реквизиты из подключения.
    #
    repository: (
        PlatformConnectionRepository
    )

    secret_protector: (
        SecretProtector
    )

    def connect(
        self,
        broker: BrokerType,
        mode: TradingAccountMode,
        credentials: dict[
            str,
            str,
        ],
    ) -> PlatformConnection:
        normalized = (
            self
            ._normalize_credentials(
                credentials
            )
        )

        self._validate_credentials(
            broker=broker,

            credentials=(
                normalized
            ),
        )

        if (
            self.repository
            .exists_for(
                broker=broker,

                mode=mode,
            )
        ):
            raise ValueError(
                "Platform is already "
                "connected for this "
                "broker and mode"
            )

        now = datetime.now(
            timezone.utc
        )

        platform = (
            PlatformConnection(
                id=str(
                    uuid4()
                ),

                broker=broker,

                mode=mode,

                created_at=now,

                updated_at=now,
            )
        )

        self.repository.save(
            platform=platform,

            protected_credentials=(
                self
                ._protect_credentials(
                    normalized
                )
            ),
        )

        return platform

    def recover_from_sessions(
        self,
        states: list[TradingSessionState],
        account_service: TradingAccountService,
        legacy_token: str | None = None,
        legacy_account_id: str | None = None,
    ) -> int:
        existing = {(item.broker, item.mode) for item in self.get_all()}
        recovered = 0
        for state in states:
            try:
                account = account_service.get(state.trading_account_id)
            except KeyError:
                account = None
            try:
                if account is not None:
                    broker = account.broker
                    mode = account.mode
                    if (broker, mode) in existing:
                        continue
                    credentials = account_service.get_credentials(account.id).values
                elif (
                    legacy_token
                    and legacy_account_id == state.broker_account_id
                    and state.mode.lower() == "live"
                ):
                    broker = BrokerType.TINVEST
                    mode = TradingAccountMode.LIVE
                    credentials = {"token": legacy_token}
                else:
                    continue
                if (broker, mode) in existing:
                    continue
                self.connect(broker=broker, mode=mode, credentials=credentials)
            except (ValueError, KeyError, OSError):
                continue
            existing.add((broker, mode))
            recovered += 1
        return recovered

    def update_credentials(
        self,
        platform_id: str,
        credentials: dict[
            str,
            str,
        ],
    ) -> PlatformConnection:
        stored = (
            self.repository
            .get(
                platform_id
            )
        )

        if stored is None:
            raise KeyError(
                platform_id
            )

        normalized = (
            self
            ._normalize_credentials(
                credentials
            )
        )

        self._validate_credentials(
            broker=(
                stored
                .platform
                .broker
            ),

            credentials=(
                normalized
            ),
        )

        platform = (
            stored.platform
        )

        platform.updated_at = (
            datetime.now(
                timezone.utc
            )
        )

        self.repository.save(
            platform=platform,

            protected_credentials=(
                self
                ._protect_credentials(
                    normalized
                )
            ),
        )

        return platform

    def get(
        self,
        platform_id: str,
    ) -> PlatformConnection:
        stored = (
            self.repository
            .get(
                platform_id
            )
        )

        if stored is None:
            raise KeyError(
                platform_id
            )

        return (
            stored.platform
        )

    def get_all(
        self,
    ) -> list[
        PlatformConnection
    ]:
        return [
            item.platform

            for item
            in self.repository
            .get_all()
        ]

    def get_credentials(
        self,
        platform_id: str,
    ) -> dict[
        str,
        str,
    ]:
        stored = (
            self.repository
            .get(
                platform_id
            )
        )

        if stored is None:
            raise KeyError(
                platform_id
            )

        decrypted = (
            self.secret_protector
            .unprotect(
                stored
                .protected_credentials
            )
        )

        values = json.loads(
            decrypted
        )

        if not isinstance(
            values,
            dict,
        ):
            raise ValueError(
                "Invalid stored credentials"
            )

        return {
            str(key):
                str(value)

            for (
                key,
                value,
            )
            in values.items()
        }

    def delete(
        self,
        platform_id: str,
    ) -> None:
        if (
            self.repository
            .get(
                platform_id
            )
            is None
        ):
            raise KeyError(
                platform_id
            )

        self.repository.delete(
            platform_id
        )

    def _protect_credentials(
        self,
        credentials: dict[
            str,
            str,
        ],
    ) -> str:
        serialized = (
            json.dumps(
                credentials,

                ensure_ascii=False,

                sort_keys=True,
            )
        )

        return (
            self.secret_protector
            .protect(
                serialized
            )
        )

    @staticmethod
    def _normalize_credentials(
        credentials: dict[
            str,
            str,
        ],
    ) -> dict[str, str]:
        normalized = {
            str(key).strip():
                str(value).strip()

            for (
                key,
                value,
            )
            in credentials.items()

            if (
                str(key).strip()
                and str(value).strip()
            )
        }

        if not normalized:
            raise ValueError(
                "Credentials are required"
            )

        return normalized

    @staticmethod
    def _validate_credentials(
        broker: BrokerType,
        credentials: dict[
            str,
            str,
        ],
    ) -> None:
        if (
            broker
            == BrokerType.TINVEST
        ):
            if not (
                credentials.get(
                    "token"
                )
            ):
                raise ValueError(
                    "T-Invest token "
                    "is required"
                )

            return

        if (
            broker
            == BrokerType.BYBIT
        ):
            if not (
                credentials.get(
                    "api_key"
                )
            ):
                raise ValueError(
                    "Bybit API key "
                    "is required"
                )

            if not (
                credentials.get(
                    "api_secret"
                )
            ):
                raise ValueError(
                    "Bybit API secret "
                    "is required"
                )
