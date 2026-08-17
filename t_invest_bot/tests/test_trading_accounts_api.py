from __future__ import annotations

from datetime import (
    datetime,
    timezone,
)
from decimal import Decimal

from fastapi.testclient import (
    TestClient,
)

import web.api as api_module

from domain.trading_account import (
    BrokerType,
    CommissionMode,
    TradingAccount,
    TradingAccountMode,
)


class FakeCredentials:
    def __init__(
        self,
        values: dict[
            str,
            str,
        ],
    ) -> None:
        self.values = values

    def get(
        self,
        key: str,
    ):
        return self.values.get(
            key
        )

    def require(
        self,
        key: str,
    ) -> str:
        value = self.get(
            key
        )

        if not value:
            raise ValueError(
                key
            )

        return value


class FakeTradingAccountService:
    def __init__(
        self,
    ) -> None:
        self.accounts: dict[
            str,
            TradingAccount,
        ] = {}

        self.credentials: dict[
            str,
            dict[str, str],
        ] = {}

        self.sequence = 0

    def create(
        self,
        name,
        broker,
        broker_account_id,
        credentials,
        mode,
        commission_mode,
        custom_buy_commission_percent,
        custom_sell_commission_percent,
        enabled,
    ):
        self.sequence += 1

        account_id = (
            f"account-{self.sequence}"
        )

        now = datetime.now(
            timezone.utc
        )

        account = TradingAccount(
            id=account_id,

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

        self.accounts[
            account_id
        ] = account

        self.credentials[
            account_id
        ] = dict(
            credentials
        )

        return account

    def get_all(
        self,
    ):
        return list(
            self.accounts.values()
        )

    def get(
        self,
        account_id,
    ):
        if (
            account_id
            not in self.accounts
        ):
            raise KeyError(
                account_id
            )

        return self.accounts[
            account_id
        ]

    def get_credentials(
        self,
        account_id,
    ):
        if (
            account_id
            not in self.credentials
        ):
            raise KeyError(
                account_id
            )

        return FakeCredentials(
            self.credentials[
                account_id
            ]
        )

    def update(
        self,
        account_id,
        name=None,
        broker=None,
        broker_account_id=None,
        credentials=None,
        mode=None,
        commission_mode=None,
        custom_buy_commission_percent=None,
        custom_sell_commission_percent=None,
        enabled=None,
    ):
        account = self.get(
            account_id
        )

        if name is not None:
            account.name = name

        if broker is not None:
            account.broker = broker

        if (
            broker_account_id
            is not None
        ):
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
            account.custom_buy_commission_percent = (
                custom_buy_commission_percent
            )

        if (
            custom_sell_commission_percent
            is not None
        ):
            account.custom_sell_commission_percent = (
                custom_sell_commission_percent
            )

        if enabled is not None:
            account.enabled = (
                enabled
            )

        if credentials is not None:
            self.credentials[
                account_id
            ] = dict(
                credentials
            )

        account.updated_at = (
            datetime.now(
                timezone.utc
            )
        )

        return account

    def delete(
        self,
        account_id,
    ):
        if (
            account_id
            not in self.accounts
        ):
            raise KeyError(
                account_id
            )

        self.accounts.pop(
            account_id
        )

        self.credentials.pop(
            account_id,
            None,
        )


def test_brokers_endpoint_contains_tinvest(
    monkeypatch,
) -> None:
    client = TestClient(
        api_module.app
    )

    response = client.get(
        "/api/brokers"
    )

    assert (
        response.status_code
        == 200
    )

    brokers = (
        response.json()[
            "brokers"
        ]
    )

    tinvest = next(
        item
        for item
        in brokers
        if (
            item["id"]
            == "tinvest"
        )
    )

    assert (
        tinvest["supported"]
        is True
    )

    assert (
        tinvest[
            "credential_fields"
        ][0]["key"]
        == "token"
    )


def test_create_account_does_not_return_credentials(
    monkeypatch,
) -> None:
    service = (
        FakeTradingAccountService()
    )

    monkeypatch.setattr(
        api_module,
        "trading_account_service",
        service,
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

            "credentials": {
                "token":
                    "SECRET_TOKEN",
            },

            "mode":
                "live",

            "commission_mode":
                "investor_030",

            "enabled":
                True,
        },
    )

    assert (
        response.status_code
        == 201
    )

    data = response.json()

    assert (
        data["name"]
        == "Основной"
    )

    assert (
        data["broker"]
        == "tinvest"
    )

    assert (
        data[
            "broker_account_id"
        ]
        == "2011718042"
    )

    #
    # Секреты обратно
    # никогда не отдаём.
    #
    assert (
        "credentials"
        not in data
    )

    assert (
        "token"
        not in data
    )

    assert (
        data[
            "credentials_configured"
        ]
        is True
    )


def test_get_accounts_returns_created_account(
    monkeypatch,
) -> None:
    service = (
        FakeTradingAccountService()
    )

    monkeypatch.setattr(
        api_module,
        "trading_account_service",
        service,
    )

    service.create(
        name="Основной",

        broker=(
            BrokerType.TINVEST
        ),

        broker_account_id=(
            "123"
        ),

        credentials={
            "token":
                "secret",
        },

        mode=(
            TradingAccountMode.LIVE
        ),

        commission_mode=(
            CommissionMode
            .TRADER_005
        ),

        custom_buy_commission_percent=None,

        custom_sell_commission_percent=None,

        enabled=True,
    )

    client = TestClient(
        api_module.app
    )

    response = client.get(
        "/api/accounts"
    )

    assert (
        response.status_code
        == 200
    )

    accounts = (
        response.json()[
            "accounts"
        ]
    )

    assert (
        len(accounts)
        == 1
    )

    assert (
        accounts[0][
            "expected_buy_commission_percent"
        ]
        == "0.05"
    )

    assert (
        accounts[0][
            "expected_sell_commission_percent"
        ]
        == "0.05"
    )


def test_update_account(
    monkeypatch,
) -> None:
    service = (
        FakeTradingAccountService()
    )

    monkeypatch.setattr(
        api_module,
        "trading_account_service",
        service,
    )

    account = service.create(
        name="Старое имя",

        broker=(
            BrokerType.TINVEST
        ),

        broker_account_id="123",

        credentials={
            "token":
                "secret",
        },

        mode=(
            TradingAccountMode.LIVE
        ),

        commission_mode=(
            CommissionMode.AUTO
        ),

        custom_buy_commission_percent=None,

        custom_sell_commission_percent=None,

        enabled=True,
    )

    client = TestClient(
        api_module.app
    )

    response = client.put(
        (
            "/api/accounts/"
            f"{account.id}"
        ),

        json={
            "name":
                "Новое имя",

            "commission_mode":
                "trader_005",
        },
    )

    assert (
        response.status_code
        == 200
    )

    data = response.json()

    assert (
        data["name"]
        == "Новое имя"
    )

    assert (
        data[
            "commission_mode"
        ]
        == "trader_005"
    )


def test_delete_account(
    monkeypatch,
) -> None:
    service = (
        FakeTradingAccountService()
    )

    monkeypatch.setattr(
        api_module,
        "trading_account_service",
        service,
    )

    account = service.create(
        name="Удаляемый",

        broker=(
            BrokerType.TINVEST
        ),

        broker_account_id="123",

        credentials={
            "token":
                "secret",
        },

        mode=(
            TradingAccountMode.LIVE
        ),

        commission_mode=(
            CommissionMode.AUTO
        ),

        custom_buy_commission_percent=None,

        custom_sell_commission_percent=None,

        enabled=True,
    )

    client = TestClient(
        api_module.app
    )

    response = client.delete(
        (
            "/api/accounts/"
            f"{account.id}"
        )
    )

    assert (
        response.status_code
        == 200
    )

    assert (
        response.json()[
            "status"
        ]
        == "deleted"
    )

    response = client.get(
        (
            "/api/accounts/"
            f"{account.id}"
        )
    )

    assert (
        response.status_code
        == 404
    )


def test_unsupported_broker_cannot_be_added_yet(
    monkeypatch,
) -> None:
    service = (
        FakeTradingAccountService()
    )

    monkeypatch.setattr(
        api_module,
        "trading_account_service",
        service,
    )

    client = TestClient(
        api_module.app
    )

    response = client.post(
        "/api/accounts",

        json={
            "name":
                "БКС",

            "broker":
                "bcs",

            "broker_account_id":
                "123",

            "credentials": {
                "token":
                    "secret",
            },
        },
    )

    assert (
        response.status_code
        == 400
    )
