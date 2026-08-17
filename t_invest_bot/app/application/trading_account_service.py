from __future__ import annotations

import json

from dataclasses import dataclass
from datetime import (
    datetime,
    timezone,
)
from decimal import Decimal
from typing import Protocol
from uuid import uuid4

from domain.trading_account import (
    BrokerType,
    CommissionMode,
    TradingAccount,
    TradingAccountMode,
)
from infrastructure.sqlite.trading_account_repository import (
    TradingAccountRepository,
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
class TradingAccountCredentials:
    values: dict[
        str,
        str,
    ]

    def get(
        self,
        key: str,
    ) -> str | None:
        return (
            self.values.get(
                key
            )
        )

    def require(
        self,
        key: str,
    ) -> str:
        value = (
            self.get(
                key
            )
        )

        if not value:
            raise ValueError(
                "Credential is missing: "
                f"{key}"
            )

        return value


@dataclass(slots=True)
class TradingAccountService:
    repository: (
        TradingAccountRepository
    )

    secret_protector: (
        SecretProtector
    )

    def create(
        self,

        name: str,

        broker: BrokerType,

        broker_account_id: str,

        credentials: dict[
            str,
            str,
        ],

        mode: (
            TradingAccountMode
        ) = TradingAccountMode.LIVE,

        commission_mode: (
            CommissionMode
        ) = CommissionMode.AUTO,

        custom_buy_commission_percent: (
            Decimal | None
        ) = None,

        custom_sell_commission_percent: (
            Decimal | None
        ) = None,

        enabled: bool = True,
    ) -> TradingAccount:
        name = name.strip()

        broker_account_id = (
            broker_account_id.strip()
        )

        if not name:
            raise ValueError(
                "Account name is required"
            )

        if not broker_account_id:
            raise ValueError(
                "Broker account ID "
                "is required"
            )

        normalized_credentials = (
            self._normalize_credentials(
                credentials
            )
        )

        self._validate_credentials(
            broker=broker,

            credentials=(
                normalized_credentials
            ),
        )

        self._validate_commission(
            commission_mode=(
                commission_mode
            ),

            custom_buy=(
                custom_buy_commission_percent
            ),

            custom_sell=(
                custom_sell_commission_percent
            ),
        )

        if (
            self.repository
            .broker_account_exists(
                broker=broker,

                broker_account_id=(
                    broker_account_id
                ),

                mode=mode,
            )
        ):
            raise ValueError(
                "Trading account already "
                "exists for this broker, "
                "account and mode"
            )

        now = datetime.now(
            timezone.utc
        )

        account = TradingAccount(
            id=str(
                uuid4()
            ),

            name=name,

            broker=broker,

            broker_account_id=(
                broker_account_id
            ),

            mode=mode,

            commission_mode=(
                commission_mode
            ),

            custom_buy_commission_percent=(
                custom_buy_commission_percent
            ),

            custom_sell_commission_percent=(
                custom_sell_commission_percent
            ),

            enabled=enabled,

            created_at=now,

            updated_at=now,
        )

        protected_credentials = (
            self._protect_credentials(
                normalized_credentials
            )
        )

        self.repository.save(
            account=account,

            protected_credentials=(
                protected_credentials
            ),
        )

        return account

    def update(
        self,

        account_id: str,

        name: (
            str | None
        ) = None,

        broker: (
            BrokerType | None
        ) = None,

        broker_account_id: (
            str | None
        ) = None,

        credentials: (
            dict[str, str]
            | None
        ) = None,

        mode: (
            TradingAccountMode
            | None
        ) = None,

        commission_mode: (
            CommissionMode
            | None
        ) = None,

        custom_buy_commission_percent: (
            Decimal | None
        ) = None,

        custom_sell_commission_percent: (
            Decimal | None
        ) = None,

        enabled: (
            bool | None
        ) = None,
    ) -> TradingAccount:
        stored = (
            self.repository.get(
                account_id
            )
        )

        if stored is None:
            raise KeyError(
                account_id
            )

        account = (
            stored.account
        )

        if name is not None:
            name = name.strip()

            if not name:
                raise ValueError(
                    "Account name "
                    "is required"
                )

            account.name = name

        if broker is not None:
            account.broker = broker

        if (
            broker_account_id
            is not None
        ):
            broker_account_id = (
                broker_account_id
                .strip()
            )

            if not broker_account_id:
                raise ValueError(
                    "Broker account ID "
                    "is required"
                )

            account.broker_account_id = (
                broker_account_id
            )

        if mode is not None:
            account.mode = mode

        if (
            commission_mode
            is not None
        ):
            account.commission_mode = (
                commission_mode
            )

        if (
            custom_buy_commission_percent
            is not None
        ):
            account\
                .custom_buy_commission_percent = (
                    custom_buy_commission_percent
                )

        if (
            custom_sell_commission_percent
            is not None
        ):
            account\
                .custom_sell_commission_percent = (
                    custom_sell_commission_percent
                )

        if enabled is not None:
            account.enabled = enabled

        self._validate_commission(
            commission_mode=(
                account
                .commission_mode
            ),

            custom_buy=(
                account
                .custom_buy_commission_percent
            ),

            custom_sell=(
                account
                .custom_sell_commission_percent
            ),
        )

        if (
            self.repository
            .broker_account_exists(
                broker=(
                    account.broker
                ),

                broker_account_id=(
                    account
                    .broker_account_id
                ),

                mode=(
                    account.mode
                ),

                exclude_id=(
                    account.id
                ),
            )
        ):
            raise ValueError(
                "Trading account already "
                "exists for this broker, "
                "account and mode"
            )

        protected_credentials = (
            stored
            .protected_credentials
        )

        if credentials is not None:
            normalized_credentials = (
                self._normalize_credentials(
                    credentials
                )
            )

            self._validate_credentials(
                broker=(
                    account.broker
                ),

                credentials=(
                    normalized_credentials
                ),
            )

            protected_credentials = (
                self._protect_credentials(
                    normalized_credentials
                )
            )

        account.updated_at = (
            datetime.now(
                timezone.utc
            )
        )

        self.repository.save(
            account=account,

            protected_credentials=(
                protected_credentials
            ),
        )

        return account

    def get(
        self,
        account_id: str,
    ) -> TradingAccount:
        stored = (
            self.repository.get(
                account_id
            )
        )

        if stored is None:
            raise KeyError(
                account_id
            )

        return (
            stored.account
        )

    def get_all(
        self,
    ) -> list[
        TradingAccount
    ]:
        return [
            item.account
            for item
            in self.repository
            .get_all()
        ]

    def get_enabled(
        self,
    ) -> list[
        TradingAccount
    ]:
        return [
            item.account
            for item
            in self.repository
            .get_enabled()
        ]

    def get_credentials(
        self,
        account_id: str,
    ) -> TradingAccountCredentials:
        stored = (
            self.repository.get(
                account_id
            )
        )

        if stored is None:
            raise KeyError(
                account_id
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

        return (
            TradingAccountCredentials(
                values={
                    str(key):
                        str(value)

                    for (
                        key,
                        value,
                    )
                    in values.items()
                }
            )
        )

    def get_token(
        self,
        account_id: str,
    ) -> str:
        """
        Legacy helper для T-Invest.

        После подключения BrokerAdapter
        основной код больше не должен
        напрямую вызывать этот метод.
        """

        account = self.get(
            account_id
        )

        if (
            account.broker
            != BrokerType.TINVEST
        ):
            raise ValueError(
                "get_token() is only "
                "available for T-Invest"
            )

        return (
            self
            .get_credentials(
                account_id
            )
            .require(
                "token"
            )
        )

    def delete(
        self,
        account_id: str,
    ) -> None:
        if (
            self.repository.get(
                account_id
            )
            is None
        ):
            raise KeyError(
                account_id
            )

        self.repository.delete(
            account_id
        )

    def set_detected_commission(
        self,

        account_id: str,

        buy_percent: (
            Decimal | None
        ) = None,

        sell_percent: (
            Decimal | None
        ) = None,
    ) -> TradingAccount:
        stored = (
            self.repository.get(
                account_id
            )
        )

        if stored is None:
            raise KeyError(
                account_id
            )

        account = (
            stored.account
        )

        if (
            buy_percent
            is not None
        ):
            self._validate_percent(
                buy_percent
            )

            account\
                .detected_buy_commission_percent = (
                    buy_percent
                )

        if (
            sell_percent
            is not None
        ):
            self._validate_percent(
                sell_percent
            )

            account\
                .detected_sell_commission_percent = (
                    sell_percent
                )

        account.updated_at = (
            datetime.now(
                timezone.utc
            )
        )

        self.repository.save(
            account=account,

            protected_credentials=(
                stored
                .protected_credentials
            ),
        )

        return account

    def _protect_credentials(
        self,
        credentials: dict[
            str,
            str,
        ],
    ) -> str:
        serialized = json.dumps(
            credentials,

            ensure_ascii=False,

            sort_keys=True,
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

    def _validate_credentials(
        self,

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

        #
        # Для будущих брокеров
        # требования будут находиться
        # в соответствующем adapter.
        #
        # Поэтому domain/service
        # не нужно переписывать.
        #

    def _validate_commission(
        self,

        commission_mode: (
            CommissionMode
        ),

        custom_buy: (
            Decimal | None
        ),

        custom_sell: (
            Decimal | None
        ),
    ) -> None:
        if (
            commission_mode
            != CommissionMode.CUSTOM
        ):
            return

        if (
            custom_buy is None
            or custom_sell is None
        ):
            raise ValueError(
                "CUSTOM commission mode "
                "requires BUY and SELL "
                "commission percentages"
            )

        self._validate_percent(
            custom_buy
        )

        self._validate_percent(
            custom_sell
        )

    @staticmethod
    def _validate_percent(
        value: Decimal,
    ) -> None:
        if (
            value < Decimal("0")
        ):
            raise ValueError(
                "Commission percent "
                "cannot be negative"
            )

        if (
            value > Decimal("10")
        ):
            raise ValueError(
                "Commission percent "
                "is too large"
            )
