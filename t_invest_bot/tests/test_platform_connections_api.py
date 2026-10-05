from __future__ import annotations

from datetime import (
    datetime,
    timezone,
)
from types import SimpleNamespace
from application.trading_account_service import TradingAccountCredentials

from fastapi.testclient import (
    TestClient,
)

import web.api as api_module

from application.platform_connection_service import (
    PlatformConnectionService,
)
from domain.platform_connection import (
    PlatformConnection,
)
from domain.trading_account import (
    BrokerType,
    CommissionMode,
    TradingAccount,
    TradingAccountMode,
)
from infrastructure.brokers.base import (
    BrokerAccountInfo,
)
from infrastructure.sqlite.platform_connection_repository import (
    PlatformConnectionRepository,
)


class FakePlatformConnectionService:
    def __init__(
        self,
    ) -> None:
        self.platforms: dict[
            str,
            PlatformConnection,
        ] = {}

        self.credentials: dict[
            str,
            dict[str, str],
        ] = {}

        self.sequence = 0

    def connect(
        self,
        broker,
        mode,
        credentials,
    ):
        normalized = {
            key: (
                value
            ).strip()

            for (
                key,
                value,
            )
            in credentials.items()

            if (
                value
            ).strip()
        }

        if not normalized:
            raise ValueError(
                "Credentials are required"
            )

        if broker == BrokerType.TINVEST and not normalized.get(
            "token"
        ):
            raise ValueError(
                "T-Invest token "
                "is required"
            )

        for platform in (
            self
            .platforms
            .values()
        ):
            if (
                platform
                .broker
                == broker

                and platform
                .mode
                == mode
            ):
                raise ValueError(
                    "Platform is already "
                    "connected for this "
                    "broker and mode"
                )

        self.sequence += 1

        platform_id = (
            f"platform-{self.sequence}"
        )

        now = datetime.now(
            timezone.utc
        )

        self.platforms[
            platform_id
        ] = (
            PlatformConnection(
                id=platform_id,

                broker=broker,

                mode=mode,

                created_at=now,

                updated_at=now,
            )
        )

        self.credentials[
            platform_id
        ] = (
            normalized
        )

        return (
            self
            .platforms[
                platform_id
            ]
        )

    def update_credentials(
        self,
        platform_id,
        credentials,
    ):
        if (
            platform_id
            not in (
                self
                .platforms
            )
        ):
            raise KeyError(
                platform_id
            )

        self.credentials[
            platform_id
        ] = (
            dict(
                credentials
            )
        )

        return (
            self
            .platforms[
                platform_id
            ]
        )

    def get(
        self,
        platform_id,
    ):
        try:
            return (
                self
                .platforms[
                    platform_id
                ]
            )

        except KeyError as error:
            raise KeyError(
                platform_id
            ) from error

    def get_all(
        self,
    ):
        return list(
            self
            .platforms
            .values()
        )

    def get_credentials(
        self,
        platform_id,
    ):
        try:
            return (
                self
                .credentials[
                    platform_id
                ]
            )

        except KeyError as error:
            raise KeyError(
                platform_id
            ) from error

    def delete(
        self,
        platform_id,
    ):
        if (
            platform_id
            not in (
                self
                .platforms
            )
        ):
            raise KeyError(
                platform_id
            )

        self.platforms.pop(
            platform_id
        )

        self.credentials.pop(
            platform_id,
            None,
        )


class FakeTradingAccountService:
    def __init__(
        self,
    ) -> None:
        self.accounts: list[
            TradingAccount
        ] = []

        self.created_credentials = {}

    def get_all(
        self,
    ):
        return (
            self.accounts
        )

    def create(
        self,
        name,
        broker,
        broker_account_id,
        credentials,
        mode,
        base_currency=None,
        commission_mode=(
            CommissionMode
            .AUTO
        ),
        custom_buy_commission_percent=None,
        custom_sell_commission_percent=None,
        enabled=True,
    ):
        now = datetime.now(
            timezone.utc
        )

        account = (
            TradingAccount(
                id=(
                    f"account-{len(self.accounts) + 1}"
                ),

                name=name,

                broker=broker,

                broker_account_id=(
                    broker_account_id
                ),

                mode=mode,

                base_currency=(
                    base_currency
                ),

                commission_mode=(
                    commission_mode
                ),

                enabled=enabled,

                created_at=now,

                updated_at=now,
            )
        )

        self.accounts.append(
            account
        )

        self.created_credentials[
            account.id
        ] = (
            credentials
        )

        return account


class FakeBrokerAdapter:
    def __init__(
        self,
        accounts,
    ) -> None:
        self.accounts = (
            accounts
        )

    def get_accounts(
        self,
        credentials,
        mode,
    ):
        return (
            self.accounts
        )

    def get_portfolio(
        self,
        credentials,
        broker_account_id,
        mode,
    ):
        raise RuntimeError(
            "portfolio unavailable"
        )


class FakeBrokerRegistry:
    def __init__(
        self,
        adapter,
    ) -> None:
        self.adapter = (
            adapter
        )

    def is_supported(
        self,
        broker,
    ):
        return (
            broker
            == (
                BrokerType
                .TINVEST
            )
        )

    def get(
        self,
        broker,
    ):
        if not (
            self.is_supported(
                broker
            )
        ):
            raise KeyError(
                broker
            )

        return (
            self.adapter
        )


def test_bybit_account_is_discovered_from_platform_without_manual_id_or_commission(monkeypatch):
    platforms = FakePlatformConnectionService()
    platform = platforms.connect(BrokerType.BYBIT, TradingAccountMode.LIVE, {"api_key": "test", "api_secret": "test"})
    accounts = FakeTradingAccountService()
    adapter = FakeBrokerAdapter([BrokerAccountInfo("UNIFIED", "Bybit", "active", "unified")])
    monkeypatch.setattr(api_module, "platform_connection_service", platforms)
    monkeypatch.setattr(api_module, "trading_account_service", accounts)
    monkeypatch.setattr(api_module, "broker_registry", SimpleNamespace(is_supported=lambda _: True, get=lambda _: adapter))
    monkeypatch.setattr(api_module, "_balance_backfill_account", lambda _: None)
    response = TestClient(api_module.app).post("/api/accounts", json={
        "name": "Bybit", "broker": "bybit", "platform_id": platform.id, "base_currency": "USDT",
        "commission_mode": "custom", "custom_buy_commission_percent": "99", "custom_sell_commission_percent": "99",
    })
    assert response.status_code == 201, response.text
    assert response.json()["broker_account_id"] == "UNIFIED"
    assert response.json()["commission_mode"] == "auto"
    assert "api_secret" not in response.text


def test_new_platforms_and_accounts_reject_sandbox_without_changing_existing_data(monkeypatch):
    platforms = FakePlatformConnectionService()
    accounts = FakeTradingAccountService()
    monkeypatch.setattr(api_module, "platform_connection_service", platforms)
    monkeypatch.setattr(api_module, "trading_account_service", accounts)
    client = TestClient(api_module.app)
    assert client.post("/api/platforms", json={"broker": "tinvest", "mode": "sandbox", "credentials": {"token": "test"}}).status_code == 400
    assert client.post("/api/accounts", json={"name": "sandbox", "broker": "tinvest", "mode": "sandbox", "broker_account_id": "1", "credentials": {"token": "test"}}).status_code == 400
    assert not platforms.platforms and not accounts.accounts


def test_platform_connect_list_update_delete(
    monkeypatch,
) -> None:
    service = (
        FakePlatformConnectionService()
    )

    monkeypatch.setattr(
        api_module,
        "platform_connection_service",
        service,
    )

    client = TestClient(
        api_module.app
    )

    response = client.post(
        "/api/platforms",

        json={
            "broker":
                "tinvest",

            "mode":
                "live",

            "credentials": {
                "token":
                    "SECRET_TOKEN",
            },
        },
    )

    assert (
        response.status_code
        == 201
    )

    platform = (
        response.json()
    )

    assert (
        platform[
            "broker"
        ]
        == "tinvest"
    )

    assert (
        platform["mode"]
        == "live"
    )

    #
    # Секреты обратно
    # никогда не отдаём.
    #
    assert (
        "credentials"
        not in platform
    )

    assert (
        "SECRET_TOKEN"
        not in (
            response.text
        )
    )

    listed = client.get(
        "/api/platforms"
    )

    assert (
        listed.status_code
        == 200
    )

    assert (
        len(
            listed.json()[
                "platforms"
            ]
        )
        == 1
    )

    updated = client.put(
        f"/api/platforms/{platform['id']}",

        json={
            "credentials": {
                "token":
                    "NEW_TOKEN",
            },
        },
    )

    assert (
        updated.status_code
        == 200
    )

    assert (
        service
        .credentials[
            platform[
                "id"
            ]
        ]
        == {
            "token":
                "NEW_TOKEN",
        }
    )

    deleted = client.delete(
        f"/api/platforms/{platform['id']}"
    )

    assert (
        deleted.status_code
        == 200
    )

    missing = client.delete(
        f"/api/platforms/{platform['id']}"
    )

    assert (
        missing.status_code
        == 404
    )


def test_platform_duplicate_rejected(
    monkeypatch,
) -> None:
    service = (
        FakePlatformConnectionService()
    )

    monkeypatch.setattr(
        api_module,
        "platform_connection_service",
        service,
    )

    client = TestClient(
        api_module.app
    )

    first = client.post(
        "/api/platforms",

        json={
            "broker":
                "tinvest",

            "mode":
                "live",

            "credentials": {
                "token":
                    "TOKEN_1",
            },
        },
    )

    assert (
        first.status_code
        == 201
    )

    second = client.post(
        "/api/platforms",

        json={
            "broker":
                "tinvest",

            "mode":
                "live",

            "credentials": {
                "token":
                    "TOKEN_2",
            },
        },
    )

    assert (
        second.status_code
        == 400
    )


def test_create_account_via_platform(
    monkeypatch,
) -> None:
    platforms = (
        FakePlatformConnectionService()
    )

    accounts = (
        FakeTradingAccountService()
    )

    platform = (
        platforms.connect(
            broker=(
                BrokerType
                .TINVEST
            ),

            mode=(
                TradingAccountMode
                .LIVE
            ),

            credentials={
                "token":
                    "PLATFORM_TOKEN",
            },
        )
    )

    monkeypatch.setattr(
        api_module,
        "platform_connection_service",
        platforms,
    )

    monkeypatch.setattr(
        api_module,
        "trading_account_service",
        accounts,
    )

    client = TestClient(
        api_module.app
    )

    response = client.post(
        "/api/accounts",

        json={
            "name":
                "Основной",

            "broker":
                "tinvest",

            "broker_account_id":
                "2011718042",

            "platform_id":
                platform.id,

            "mode":
                "live",

            "commission_mode":
                "auto",
        },
    )

    assert (
        response.status_code
        == 201
    )

    assert (
        accounts
        .created_credentials[
            response
            .json()[
                "id"
            ]
        ]
        == {
            "token":
                "PLATFORM_TOKEN",
        }
    )


def test_create_account_platform_mismatch(
    monkeypatch,
) -> None:
    platforms = (
        FakePlatformConnectionService()
    )

    accounts = (
        FakeTradingAccountService()
    )

    platform = (
        platforms.connect(
            broker=(
                BrokerType
                .TINVEST
            ),

            mode=(
                TradingAccountMode
                .LIVE
            ),

            credentials={
                "token":
                    "PLATFORM_TOKEN",
            },
        )
    )

    monkeypatch.setattr(
        api_module,
        "platform_connection_service",
        platforms,
    )

    monkeypatch.setattr(
        api_module,
        "trading_account_service",
        accounts,
    )

    client = TestClient(
        api_module.app
    )

    response = client.post(
        "/api/accounts",

        json={
            "name":
                "Песочница",

            "broker":
                "tinvest",

            "broker_account_id":
                "1",

            "platform_id":
                platform.id,

            "mode":
                "sandbox",
        },
    )

    assert (
        response.status_code
        == 400
    )

    assert (
        not (
            accounts
            .accounts
        )
    )


def test_discover_platform_marks_already_added(
    monkeypatch,
) -> None:
    platforms = (
        FakePlatformConnectionService()
    )

    accounts = (
        FakeTradingAccountService()
    )

    accounts.accounts.append(
        TradingAccount(
            id=(
                "account-existing"
            ),

            name=(
                "Уже добавлен"
            ),

            broker=(
                BrokerType
                .TINVEST
            ),

            broker_account_id=(
                "111"
            ),

            mode=(
                TradingAccountMode
                .LIVE
            ),
        )
    )

    platform = (
        platforms.connect(
            broker=(
                BrokerType
                .TINVEST
            ),

            mode=(
                TradingAccountMode
                .LIVE
            ),

            credentials={
                "token":
                    "PLATFORM_TOKEN",
            },
        )
    )

    adapter = (
        FakeBrokerAdapter(
            accounts=[
                BrokerAccountInfo(
                    broker_account_id=(
                        "111"
                    ),

                    name=(
                        "Основной"
                    ),

                    status="1",

                    account_type=(
                        "1"
                    ),
                ),

                BrokerAccountInfo(
                    broker_account_id=(
                        "222"
                    ),

                    name=(
                        "ИИС"
                    ),

                    status="1",

                    account_type=(
                        "2"
                    ),
                ),
            ],
        )
    )

    monkeypatch.setattr(
        api_module,
        "platform_connection_service",
        platforms,
    )

    monkeypatch.setattr(
        api_module,
        "trading_account_service",
        accounts,
    )

    monkeypatch.setattr(
        api_module,
        "broker_registry",

        FakeBrokerRegistry(
            adapter
        ),
    )

    client = TestClient(
        api_module.app
    )

    response = client.post(
        f"/api/platforms/{platform.id}/discover"
    )

    assert (
        response.status_code
        == 200
    )

    data = (
        response.json()
    )

    assert (
        data["success"]
        is True
    )

    by_id = {
        item[
            "broker_account_id"
        ]: item

        for item
        in data[
            "accounts"
        ]
    }

    assert (
        by_id["111"][
            "already_added"
        ]
        is True
    )

    assert (
        by_id["222"][
            "already_added"
        ]
        is False
    )


class IdentitySecretProtector:
    def protect(
        self,
        value: str,
    ) -> str:
        return value

    def unprotect(
        self,
        value: str,
    ) -> str:
        return value


def test_platform_recovery_from_active_sessions_is_idempotent(tmp_path) -> None:
    service = PlatformConnectionService(
        repository=PlatformConnectionRepository(str(tmp_path / "platforms.db")),
        secret_protector=IdentitySecretProtector(),
    )
    account = TradingAccount(
        id="account-1", name="Main", broker=BrokerType.TINVEST,
        broker_account_id="broker-1", mode=TradingAccountMode.LIVE,
    )
    accounts = SimpleNamespace(
        get=lambda account_id: account,
        get_credentials=lambda account_id: TradingAccountCredentials({"token": "saved-token"}),
    )
    states = [SimpleNamespace(trading_account_id=account.id)]

    assert service.recover_from_sessions(states, accounts) == 1
    platform = service.get_all()[0]
    assert service.get_credentials(platform.id) == {"token": "saved-token"}
    assert service.recover_from_sessions(states, accounts) == 0

    service.update_credentials(platform.id, {"token": "new-token"})
    assert service.recover_from_sessions(states, accounts) == 0
    assert service.get_credentials(platform.id) == {"token": "new-token"}


def test_platform_recovery_uses_matching_legacy_account_only(tmp_path) -> None:
    service = PlatformConnectionService(
        repository=PlatformConnectionRepository(str(tmp_path / "platforms.db")),
        secret_protector=IdentitySecretProtector(),
    )

    def missing_account(account_id):
        raise KeyError(account_id)

    accounts = SimpleNamespace(get=missing_account)
    states = [SimpleNamespace(
        trading_account_id="legacy", broker_account_id="broker-1", mode="live",
    )]
    assert service.recover_from_sessions(states, accounts, "legacy-token", "other") == 0
    assert service.recover_from_sessions(states, accounts, "legacy-token", "broker-1") == 1
    assert service.get_credentials(service.get_all()[0].id) == {"token": "legacy-token"}


def test_platform_service_with_repository(
    tmp_path,
) -> None:
    repository = (
        PlatformConnectionRepository(
            db_path=str(
                tmp_path
                / "test.db"
            ),
        )
    )

    service = (
        PlatformConnectionService(
            repository=(
                repository
            ),

            secret_protector=(
                IdentitySecretProtector()
            ),
        )
    )

    platform = (
        service.connect(
            broker=(
                BrokerType
                .BYBIT
            ),

            mode=(
                TradingAccountMode
                .LIVE
            ),

            credentials={
                "api_key":
                    "KEY",

                "api_secret":
                    "SECRET",
            },
        )
    )

    assert (
        service
        .get_credentials(
            platform.id
        )
        == {
            "api_key":
                "KEY",

            "api_secret":
                "SECRET",
        }
    )

    try:
        service.connect(
            broker=(
                BrokerType
                .BYBIT
            ),

            mode=(
                TradingAccountMode
                .LIVE
            ),

            credentials={
                "api_key":
                    "KEY2",

                "api_secret":
                    "SECRET2",
            },
        )

        raised = (
            False
        )

    except ValueError:
        raised = (
            True
        )

    assert raised

    try:
        service.connect(
            broker=(
                BrokerType
                .BYBIT
            ),

            mode=(
                TradingAccountMode
                .LIVE
            ),

            credentials={
                "api_key":
                    "KEY",
            },
        )

        invalid = (
            False
        )

    except ValueError:
        invalid = (
            True
        )

    assert invalid

    service.update_credentials(
        platform.id,

        credentials={
            "api_key":
                "NEW_KEY",

            "api_secret":
                "NEW_SECRET",
        },
    )

    assert (
        service
        .get_credentials(
            platform.id
        )
        == {
            "api_key":
                "NEW_KEY",

            "api_secret":
                "NEW_SECRET",
        }
    )

    assert (
        len(
            service
            .get_all()
        )
        == 1
    )

    service.delete(
        platform.id
    )

    try:
        service.get(
            platform.id
        )

        missing = (
            False
        )

    except KeyError:
        missing = (
            True
        )

    assert missing
