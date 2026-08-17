from decimal import Decimal

from application.trading_account_service import (
    TradingAccountService,
)
from domain.trading_account import (
    BrokerType,
    CommissionMode,
    TradingAccountMode,
)
from infrastructure.sqlite.trading_account_repository import (
    TradingAccountRepository,
)


import base64


class FakeSecretProtector:
    def protect(
        self,
        value: str,
    ) -> str:
        raw = value.encode(
            "utf-8"
        )

        return (
            base64.b64encode(
                raw
            )
            .decode(
                "ascii"
            )
        )

    def unprotect(
        self,
        value: str,
    ) -> str:
        raw = (
            base64.b64decode(
                value.encode(
                    "ascii"
                )
            )
        )

        return raw.decode(
            "utf-8"
        )


def create_service(
    tmp_path,
) -> TradingAccountService:
    repository = (
        TradingAccountRepository(
            db_path=str(
                tmp_path
                / "accounts.db"
            )
        )
    )

    return TradingAccountService(
        repository=repository,

        secret_protector=(
            FakeSecretProtector()
        ),
    )


def create_tinvest_account(
    service: TradingAccountService,

    name: str = "Основной",

    broker_account_id: str = "1",

    token: str = "secret-token",

    mode: TradingAccountMode = (
        TradingAccountMode.LIVE
    ),

    commission_mode: CommissionMode = (
        CommissionMode.AUTO
    ),

    custom_buy_commission_percent: (
        Decimal | None
    ) = None,

    custom_sell_commission_percent: (
        Decimal | None
    ) = None,

    enabled: bool = True,
):
    return service.create(
        name=name,

        broker=(
            BrokerType.TINVEST
        ),

        broker_account_id=(
            broker_account_id
        ),

        credentials={
            "token": token,
        },

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
    )


def test_create_account_and_read_token(
    tmp_path,
) -> None:
    service = create_service(
        tmp_path
    )

    account = (
        create_tinvest_account(
            service=service,

            name="Основной",

            broker_account_id=(
                "2011718042"
            ),

            token="secret-token",

            commission_mode=(
                CommissionMode
                .INVESTOR_030
            ),
        )
    )

    assert (
        account.name
        == "Основной"
    )

    assert (
        account.broker
        == BrokerType.TINVEST
    )

    assert (
        account
        .broker_account_id
        == "2011718042"
    )

    assert (
        service.get_token(
            account.id
        )
        == "secret-token"
    )


def test_credentials_are_not_stored_as_plain_text(
    tmp_path,
) -> None:
    service = create_service(
        tmp_path
    )

    account = (
        create_tinvest_account(
            service=service,
        )
    )

    stored = (
        service.repository.get(
            account.id
        )
    )

    assert stored is not None

    #
    # В SQLite не должен лежать
    # исходный token.
    #
    assert (
        stored
        .protected_credentials
        != "secret-token"
    )

    assert (
        "secret-token"
        not in stored
        .protected_credentials
    )


def test_credentials_can_be_restored(
    tmp_path,
) -> None:
    service = create_service(
        tmp_path
    )

    account = (
        create_tinvest_account(
            service=service,

            token="my-token",
        )
    )

    credentials = (
        service.get_credentials(
            account.id
        )
    )

    assert (
        credentials.require(
            "token"
        )
        == "my-token"
    )


def test_investor_commission_is_point_three_percent(
    tmp_path,
) -> None:
    service = create_service(
        tmp_path
    )

    account = (
        create_tinvest_account(
            service=service,

            commission_mode=(
                CommissionMode
                .INVESTOR_030
            ),
        )
    )

    assert (
        account
        .get_expected_buy_commission_percent()
        == Decimal("0.30")
    )

    assert (
        account
        .get_expected_sell_commission_percent()
        == Decimal("0.30")
    )


def test_trader_commission_is_point_zero_five_percent(
    tmp_path,
) -> None:
    service = create_service(
        tmp_path
    )

    account = (
        create_tinvest_account(
            service=service,

            commission_mode=(
                CommissionMode
                .TRADER_005
            ),
        )
    )

    assert (
        account
        .get_expected_buy_commission_percent()
        == Decimal("0.05")
    )

    assert (
        account
        .get_expected_sell_commission_percent()
        == Decimal("0.05")
    )


def test_custom_commission(
    tmp_path,
) -> None:
    service = create_service(
        tmp_path
    )

    account = (
        create_tinvest_account(
            service=service,

            commission_mode=(
                CommissionMode.CUSTOM
            ),

            custom_buy_commission_percent=(
                Decimal("0.12")
            ),

            custom_sell_commission_percent=(
                Decimal("0.14")
            ),
        )
    )

    assert (
        account
        .get_expected_buy_commission_percent()
        == Decimal("0.12")
    )

    assert (
        account
        .get_expected_sell_commission_percent()
        == Decimal("0.14")
    )


def test_custom_commission_requires_both_values(
    tmp_path,
) -> None:
    service = create_service(
        tmp_path
    )

    try:
        create_tinvest_account(
            service=service,

            commission_mode=(
                CommissionMode.CUSTOM
            ),

            custom_buy_commission_percent=(
                Decimal("0.10")
            ),

            custom_sell_commission_percent=(
                None
            ),
        )

    except ValueError:
        pass

    else:
        raise AssertionError(
            "CUSTOM commission without "
            "SELL value was accepted"
        )


def test_auto_uses_detected_buy_commission_for_sell_prediction(
    tmp_path,
) -> None:
    service = create_service(
        tmp_path
    )

    account = (
        create_tinvest_account(
            service=service,

            commission_mode=(
                CommissionMode.AUTO
            ),
        )
    )

    #
    # Пока фактической сделки нет —
    # безопасный fallback 0.30%.
    #
    assert (
        account
        .get_expected_buy_commission_percent()
        == Decimal("0.30")
    )

    assert (
        account
        .get_expected_sell_commission_percent()
        == Decimal("0.30")
    )

    service.set_detected_commission(
        account_id=(
            account.id
        ),

        buy_percent=(
            Decimal("0.05")
        ),
    )

    restored = service.get(
        account.id
    )

    assert (
        restored
        .get_expected_buy_commission_percent()
        == Decimal("0.05")
    )

    #
    # SELL ещё не было,
    # поэтому используем найденную
    # BUY-комиссию как прогноз.
    #
    assert (
        restored
        .get_expected_sell_commission_percent()
        == Decimal("0.05")
    )


def test_auto_prefers_detected_sell_commission(
    tmp_path,
) -> None:
    service = create_service(
        tmp_path
    )

    account = (
        create_tinvest_account(
            service=service,
        )
    )

    service.set_detected_commission(
        account_id=(
            account.id
        ),

        buy_percent=(
            Decimal("0.05")
        ),

        sell_percent=(
            Decimal("0.06")
        ),
    )

    restored = service.get(
        account.id
    )

    assert (
        restored
        .get_expected_buy_commission_percent()
        == Decimal("0.05")
    )

    assert (
        restored
        .get_expected_sell_commission_percent()
        == Decimal("0.06")
    )


def test_duplicate_account_for_same_broker_mode_is_rejected(
    tmp_path,
) -> None:
    service = create_service(
        tmp_path
    )

    create_tinvest_account(
        service=service,

        name="Первый",

        broker_account_id="1",

        token="token-1",

        mode=(
            TradingAccountMode.LIVE
        ),
    )

    try:
        create_tinvest_account(
            service=service,

            name="Второй",

            broker_account_id="1",

            token="token-2",

            mode=(
                TradingAccountMode.LIVE
            ),
        )

    except ValueError:
        pass

    else:
        raise AssertionError(
            "Duplicate account "
            "was not rejected"
        )


def test_same_account_id_can_exist_in_live_and_sandbox(
    tmp_path,
) -> None:
    service = create_service(
        tmp_path
    )

    create_tinvest_account(
        service=service,

        name="LIVE",

        broker_account_id="1",

        token="live-token",

        mode=(
            TradingAccountMode.LIVE
        ),
    )

    create_tinvest_account(
        service=service,

        name="SANDBOX",

        broker_account_id="1",

        token="sandbox-token",

        mode=(
            TradingAccountMode
            .SANDBOX
        ),
    )

    assert (
        len(
            service.get_all()
        )
        == 2
    )


def test_same_broker_account_id_can_exist_for_different_brokers(
    tmp_path,
) -> None:
    service = create_service(
        tmp_path
    )

    create_tinvest_account(
        service=service,

        name="T-Invest",

        broker_account_id="100500",

        token="tinvest-token",
    )

    #
    # Для будущего брокера domain
    # не требует token.
    #
    second = service.create(
        name="Другой брокер",

        broker=(
            BrokerType.OTHER
        ),

        broker_account_id=(
            "100500"
        ),

        credentials={
            "api_key": "key",
            "api_secret": "secret",
        },

        mode=(
            TradingAccountMode.LIVE
        ),
    )

    assert (
        second.broker
        == BrokerType.OTHER
    )

    assert (
        len(
            service.get_all()
        )
        == 2
    )


def test_other_broker_credentials_are_generic(
    tmp_path,
) -> None:
    service = create_service(
        tmp_path
    )

    account = service.create(
        name="Future broker",

        broker=(
            BrokerType.OTHER
        ),

        broker_account_id="42",

        credentials={
            "api_key":
                "my-key",

            "api_secret":
                "my-secret",

            "client_id":
                "client-1",
        },
    )

    credentials = (
        service.get_credentials(
            account.id
        )
    )

    assert (
        credentials.require(
            "api_key"
        )
        == "my-key"
    )

    assert (
        credentials.require(
            "api_secret"
        )
        == "my-secret"
    )

    assert (
        credentials.require(
            "client_id"
        )
        == "client-1"
    )


def test_get_token_is_rejected_for_non_tinvest_broker(
    tmp_path,
) -> None:
    service = create_service(
        tmp_path
    )

    account = service.create(
        name="Other",

        broker=(
            BrokerType.OTHER
        ),

        broker_account_id="1",

        credentials={
            "api_key": "key",
        },
    )

    try:
        service.get_token(
            account.id
        )

    except ValueError:
        pass

    else:
        raise AssertionError(
            "get_token() unexpectedly "
            "worked for non T-Invest "
            "broker"
        )


def test_account_can_be_updated_without_replacing_credentials(
    tmp_path,
) -> None:
    service = create_service(
        tmp_path
    )

    account = (
        create_tinvest_account(
            service=service,

            name="Old name",

            token="original-token",
        )
    )

    updated = service.update(
        account_id=(
            account.id
        ),

        name="New name",
    )

    assert (
        updated.name
        == "New name"
    )

    assert (
        service.get_token(
            account.id
        )
        == "original-token"
    )


def test_account_credentials_can_be_replaced(
    tmp_path,
) -> None:
    service = create_service(
        tmp_path
    )

    account = (
        create_tinvest_account(
            service=service,

            token="old-token",
        )
    )

    service.update(
        account_id=(
            account.id
        ),

        credentials={
            "token":
                "new-token",
        },
    )

    assert (
        service.get_token(
            account.id
        )
        == "new-token"
    )


def test_disabled_accounts_are_not_returned_by_get_enabled(
    tmp_path,
) -> None:
    service = create_service(
        tmp_path
    )

    create_tinvest_account(
        service=service,

        name="Enabled",

        broker_account_id="1",

        token="one",

        mode=(
            TradingAccountMode.LIVE
        ),
    )

    create_tinvest_account(
        service=service,

        name="Disabled",

        broker_account_id="2",

        token="two",

        enabled=False,
    )

    enabled = (
        service.get_enabled()
    )

    assert (
        len(enabled)
        == 1
    )

    assert (
        enabled[0].name
        == "Enabled"
    )
