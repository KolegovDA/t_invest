from __future__ import annotations

from datetime import (
    datetime,
    timezone,
)
from types import SimpleNamespace

import pytest

from application.instrument_catalog_service import (
    InstrumentCatalogService,
)
from domain.trading_account import (
    BrokerType,
    CommissionMode,
    TradingAccount,
    TradingAccountMode,
)


class FakeCredentials:
    def __init__(
        self,
        token: str,
    ) -> None:
        self.token = token

    def require(
        self,
        key: str,
    ) -> str:
        if (
            key == "token"
            and self.token
        ):
            return self.token

        raise ValueError(
            key
        )


class FakeTradingAccountService:
    def __init__(
        self,
        accounts: list[
            TradingAccount
        ],
        tokens: (
            dict[str, str]
            | None
        ) = None,
    ) -> None:
        self.accounts = accounts
        self.tokens = (
            tokens
            or {}
        )

    def get(
        self,
        account_id: str,
    ) -> TradingAccount:
        for account in self.accounts:
            if (
                account.id
                == account_id
            ):
                return account

        raise KeyError(
            account_id
        )

    def get_enabled(
        self,
    ) -> list[
        TradingAccount
    ]:
        return [
            account
            for account
            in self.accounts
            if account.enabled
        ]

    def get_credentials(
        self,
        account_id: str,
    ) -> FakeCredentials:
        return FakeCredentials(
            self.tokens.get(
                account_id,
                "",
            )
        )


def make_account(
    account_id: str,
    mode: TradingAccountMode = (
        TradingAccountMode.SANDBOX
    ),
    enabled: bool = True,
    broker: BrokerType = (
        BrokerType.TINVEST
    ),
) -> TradingAccount:
    now = datetime.now(
        timezone.utc
    )

    return TradingAccount(
        id=account_id,
        name=account_id,
        broker=broker,
        broker_account_id=(
            f"broker-{account_id}"
        ),
        mode=mode,
        commission_mode=(
            CommissionMode.AUTO
        ),
        enabled=enabled,
        created_at=now,
        updated_at=now,
    )


def make_settings(
    sandbox_token: str | None = None,
    token: str | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        tinvest_sandbox_token=(
            sandbox_token
        ),
        tinvest_token=token,
    )


def make_service(
    accounts: list[
        TradingAccount
    ],
    tokens: (
        dict[str, str]
        | None
    ) = None,
    settings: (
        SimpleNamespace
        | None
    ) = None,
) -> InstrumentCatalogService:
    return InstrumentCatalogService(
        settings=(
            settings
            or make_settings()
        ),
        trading_account_service=(
            FakeTradingAccountService(
                accounts,
                tokens,
            )
        ),
    )


def test_resolve_token_autoselects_sandbox_account_before_live() -> None:
    service = make_service(
        accounts=[
            make_account(
                "live-1",
                mode=(
                    TradingAccountMode
                    .LIVE
                ),
            ),
            make_account(
                "sandbox-1"
            ),
        ],
        tokens={
            "live-1": (
                "live-token"
            ),
            "sandbox-1": (
                "sandbox-token"
            ),
        },
    )

    assert (
        service
        ._resolve_token(
            None
        )
        == "sandbox-token"
    )


def test_resolve_token_skips_account_without_token() -> None:
    service = make_service(
        accounts=[
            make_account(
                "sandbox-empty"
            ),
            make_account(
                "sandbox-ok"
            ),
        ],
        tokens={
            "sandbox-empty": "",
            "sandbox-ok": (
                "ok-token"
            ),
        },
    )

    assert (
        service
        ._resolve_token(
            None
        )
        == "ok-token"
    )


def test_resolve_token_falls_back_to_settings_when_no_tinvest_accounts() -> None:
    service = make_service(
        accounts=[
            make_account(
                "alfa-1",
                broker=(
                    BrokerType
                    .ALFA
                ),
            )
        ],
        tokens={},
        settings=make_settings(
            token="settings-token"
        ),
    )

    assert (
        service
        ._resolve_token(
            None
        )
        == "settings-token"
    )


def test_resolve_token_without_anything_raises() -> None:
    service = make_service(
        accounts=[],
        tokens={},
        settings=make_settings(),
    )

    with pytest.raises(
        ValueError
    ) as exc_info:
        service._resolve_token(
            None
        )

    assert (
        "T-Invest token is not configured"
        in str(
            exc_info.value
        )
    )


def test_resolve_token_uses_explicit_account() -> None:
    service = make_service(
        accounts=[
            make_account(
                "sandbox-1"
            ),
            make_account(
                "sandbox-2"
            ),
        ],
        tokens={
            "sandbox-1": (
                "first-token"
            ),
            "sandbox-2": (
                "second-token"
            ),
        },
    )

    assert (
        service
        ._resolve_token(
            "sandbox-2"
        )
        == "second-token"
    )


def test_resolve_token_explicit_account_not_found_raises() -> None:
    service = make_service(
        accounts=[],
    )

    with pytest.raises(
        ValueError
    ) as exc_info:
        service._resolve_token(
            "missing"
        )

    assert (
        "Trading account not found"
        in str(
            exc_info.value
        )
    )


def test_resolve_token_explicit_account_disabled_raises() -> None:
    service = make_service(
        accounts=[
            make_account(
                "sandbox-1",
                enabled=False,
            )
        ],
        tokens={
            "sandbox-1": "token"
        },
    )

    with pytest.raises(
        ValueError
    ) as exc_info:
        service._resolve_token(
            "sandbox-1"
        )

    assert (
        "Trading account is disabled"
        in str(
            exc_info.value
        )
    )


def test_resolve_token_explicit_non_tinvest_account_raises() -> None:
    service = make_service(
        accounts=[
            make_account(
                "alfa-1",
                broker=(
                    BrokerType
                    .ALFA
                ),
            )
        ],
        tokens={
            "alfa-1": "token"
        },
    )

    with pytest.raises(
        ValueError
    ) as exc_info:
        service._resolve_token(
            "alfa-1"
        )

    assert (
        "only for T-Invest"
        in str(
            exc_info.value
        )
    )
