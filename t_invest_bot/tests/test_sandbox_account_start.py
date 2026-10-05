from __future__ import annotations

from datetime import (
    datetime,
    timezone,
)
from types import SimpleNamespace
from unittest.mock import (
    patch,
)

import pytest

import application.multi_instrument_trading_session_factory as factory_module
import web.api as api_module

from application.multi_instrument_trading_session_factory import (
    MultiInstrumentTradingSessionFactory,
)
from application.web_runner_registry import (
    WebRunnerRegistry,
)
from domain.trading_account import (
    BrokerType,
    CommissionMode,
    TradingAccount,
    TradingAccountMode,
)
from web.api import (
    StartPlanInstrumentRequest,
    StartSandboxRequest,
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
        account: TradingAccount,
        token: str = "account-token",
    ) -> None:
        self.account = account
        self.token = token

    def get(
        self,
        account_id: str,
    ) -> TradingAccount:
        if (
            self.account.id
            != account_id
        ):
            raise KeyError(
                account_id
            )

        return self.account

    def get_enabled(
        self,
    ) -> list[
        TradingAccount
    ]:
        if (
            self.account.enabled
        ):
            return [
                self.account
            ]

        return []

    def get_credentials(
        self,
        account_id: str,
    ) -> FakeCredentials:
        return FakeCredentials(
            self.token
        )


def make_account(
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
        id="sandbox-account-1",
        name="Sandbox account",
        broker=broker,
        broker_account_id="sbx-broker-1",
        mode=mode,
        commission_mode=(
            CommissionMode.AUTO
        ),
        enabled=enabled,
        created_at=now,
        updated_at=now,
    )


def make_settings(
    sandbox_token: str | None = (
        "settings-sandbox-token"
    ),
    token: str | None = (
        "settings-token"
    ),
    selected_account: str | None = (
        "settings-account"
    ),
) -> SimpleNamespace:
    return SimpleNamespace(
        tinvest_sandbox_token=(
            sandbox_token
        ),
        tinvest_token=token,
        selected_sandbox_account_id=(
            selected_account
        ),
    )


class SandboxProviderSpy:
    opened: list[str] = []
    closed: list[str] = []
    paid_in: list[
        tuple[
            str,
            int,
        ]
    ] = []
    instances: list[
        "SandboxProviderSpy"
    ] = []

    def __init__(
        self,
        client_factory,
    ) -> None:
        self.client_factory = (
            client_factory
        )

        SandboxProviderSpy.instances.append(
            self
        )

    def open_account(
        self,
    ) -> str:
        SandboxProviderSpy.opened.append(
            "opened"
        )

        return "opened-account"

    def pay_in(
        self,
        account_id: str,
        amount,
    ):
        SandboxProviderSpy.paid_in.append(
            (
                account_id,
                amount,
            )
        )

        return 100000

    def close_account(
        self,
        account_id: str,
    ) -> None:
        SandboxProviderSpy.closed.append(
            account_id
        )


def run_factory(
    settings: SimpleNamespace,
    config,
    token: str | None = None,
    sandbox_account_id: str | None = None,
):
    captured: dict = {}

    class FakeClientFactory:
        def __init__(
            self,
            token: str,
        ) -> None:
            captured[
                "token"
            ] = token

    marker = object()

    def fake_create_context(
        self,
        **kwargs,
    ):
        captured[
            "context_kwargs"
        ] = kwargs

        return marker

    SandboxProviderSpy.opened = []
    SandboxProviderSpy.closed = []
    SandboxProviderSpy.paid_in = []

    factory = (
        MultiInstrumentTradingSessionFactory(
            settings=settings,
        )
    )

    with patch.object(
        factory_module,
        "TInvestClientFactory",
        FakeClientFactory,
    ), patch.object(
        factory_module,
        "TInvestSandboxAccountProvider",
        SandboxProviderSpy,
    ), patch.object(
        MultiInstrumentTradingSessionFactory,
        "_create_context",
        fake_create_context,
    ):
        result = (
            factory
            .create_sandbox_session(
                config=config,

                token=token,

                sandbox_account_id=(
                    sandbox_account_id
                ),
            )
        )

    captured[
        "result"
    ] = result

    return captured


def test_create_sandbox_session_uses_explicit_token_and_account() -> None:
    captured = run_factory(
        settings=make_settings(),
        config=SimpleNamespace(
            sandbox_deposit=50000,
        ),
        token="explicit-token",
        sandbox_account_id=(
            "explicit-account"
        ),
    )

    assert (
        captured["token"]
        == "explicit-token"
    )

    kwargs = (
        captured[
            "context_kwargs"
        ]
    )

    assert (
        kwargs["account_id"]
        == "explicit-account"
    )

    assert (
        kwargs["available_cash"]
        == 100000
    )

    assert (
        kwargs[
            "close_account_on_close"
        ]
        is False
    )

    assert (
        SandboxProviderSpy.opened
        == []
    )

    assert (
        SandboxProviderSpy.paid_in
        == [
            (
                "explicit-account",
                50000,
            )
        ]
    )


def test_create_sandbox_session_falls_back_to_settings() -> None:
    captured = run_factory(
        settings=make_settings(),
        config=SimpleNamespace(
            sandbox_deposit=20000,
        ),
    )

    assert (
        captured["token"]
        == "settings-sandbox-token"
    )

    assert (
        captured[
            "context_kwargs"
        ]["account_id"]
        == "settings-account"
    )

    assert (
        SandboxProviderSpy.opened
        == []
    )


def test_create_sandbox_session_opens_account_when_nothing_configured() -> None:
    captured = run_factory(
        settings=make_settings(
            sandbox_token=None,
            token="settings-token",
            selected_account=None,
        ),
        config=SimpleNamespace(
            sandbox_deposit=10000,
        ),
    )

    assert (
        captured["token"]
        == "settings-token"
    )

    assert (
        captured[
            "context_kwargs"
        ]["account_id"]
        == "opened-account"
    )

    assert (
        captured[
            "context_kwargs"
        ][
            "close_account_on_close"
        ]
        is True
    )

    assert (
        len(
            SandboxProviderSpy.opened
        )
        == 1
    )


def test_uniquify_runner_session_id_appends_counter() -> None:
    registry = WebRunnerRegistry()

    def make_runner(
        session_id: str,
    ):
        return SimpleNamespace(
            session_id=(
                session_id
            ),
            context=SimpleNamespace(
                instrument_ids_by_ticker={}
            ),
        )

    registry.register(
        make_runner(
            "sandbox:acct:abc"
        )
    )

    registry.register(
        make_runner(
            "sandbox:acct:abc#2"
        )
    )

    with patch.object(
        api_module,
        "web_runner_registry",
        registry,
    ):
        assert (
            api_module
            ._uniquify_runner_session_id(
                "sandbox:acct:abc"
            )
            == "sandbox:acct:abc#3"
        )

        assert (
            api_module
            ._uniquify_runner_session_id(
                "sandbox:acct:xyz"
            )
            == "sandbox:acct:xyz"
        )


class FakeSessionFactory:
    calls: list[dict] = []

    def __init__(
        self,
        settings=None,
        knowledge_engine=None,
        operation_log=None,
        notifier=None,
        commission_service=None,
        broker=None,
    ) -> None:
        pass

    def create_sandbox_session(
        self,
        config,
        token: str | None = None,
        sandbox_account_id: str | None = None,
    ):
        FakeSessionFactory.calls.append(
            {
                "token": token,
                "sandbox_account_id": (
                    sandbox_account_id
                ),
            }
        )

        return SimpleNamespace(
            account_id=(
                sandbox_account_id
                or "context-account"
            ),
            instrument_ids_by_ticker={},
        )


class FakeRunner:
    instances: list[
        "FakeRunner"
    ] = []

    def __init__(
        self,
        **kwargs,
    ) -> None:
        self.kwargs = kwargs
        self.session_id = kwargs[
            "session_id"
        ]
        self.context = kwargs[
            "context"
        ]
        self.is_running = False

        FakeRunner.instances.append(
            self
        )

    def start(
        self,
    ) -> None:
        pass


def run_start(
    request: StartSandboxRequest,
    registry: WebRunnerRegistry,
    account: TradingAccount,
    token: str | None = (
        "account-token"
    ),
) -> str:
    with patch.object(
        api_module,
        "trading_account_service",
        FakeTradingAccountService(
            account,
            token=(
                token
                or ""
            ),
        ),
    ), patch.object(
        api_module,
        "MultiInstrumentTradingSessionFactory",
        FakeSessionFactory,
    ), patch.object(
        api_module,
        "WebRunnerService",
        FakeRunner,
    ), patch.object(
        api_module,
        "web_runner_registry",
        registry,
    ):
        return (
            api_module
            ._try_start_real_sandbox(
                request
            )
        )


def sandbox_request(
    trading_account_id: (
        str | None
    ) = "sandbox-account-1",
) -> StartSandboxRequest:
    return StartSandboxRequest(
        trading_account_id=(
            trading_account_id
        ),
        instruments=[
            StartPlanInstrumentRequest(
                ticker="SBER",
                levels=3,
                quantity=10,
            )
        ],
    )


def test_try_start_real_sandbox_uses_account_token() -> None:
    FakeSessionFactory.calls = []
    FakeRunner.instances = []

    registry = WebRunnerRegistry()

    status = run_start(
        request=sandbox_request(),
        registry=registry,
        account=make_account(),
    )

    assert status == "started"

    assert (
        FakeSessionFactory.calls
        == [
            {
                "token": (
                    "account-token"
                ),
                "sandbox_account_id": (
                    "sbx-broker-1"
                ),
            }
        ]
    )

    runner = (
        FakeRunner.instances[
            -1
        ]
    )

    assert (
        runner
        .kwargs[
            "trading_account_id"
        ]
        == "sandbox-account-1"
    )

    assert (
        runner
        .session_id
        .startswith(
            "tinvest:"
            "sandbox-account-1:"
            "sandbox:"
        )
    )

    assert (
        registry
        .get_active_count()
        == 0
    )

    assert registry.has_session_id(
        runner.session_id
    )


def test_try_start_real_sandbox_rejects_not_sandbox_account() -> None:
    FakeSessionFactory.calls = []
    FakeRunner.instances = []

    with pytest.raises(
        ValueError
    ) as exc_info:
        run_start(
            request=(
                sandbox_request()
            ),
            registry=(
                WebRunnerRegistry()
            ),
            account=make_account(
                mode=(
                    TradingAccountMode
                    .LIVE
                )
            ),
        )

    assert (
        "not SANDBOX"
        in str(
            exc_info.value
        )
    )

    assert (
        FakeSessionFactory.calls
        == []
    )


def test_try_start_real_sandbox_autoselects_enabled_sandbox_account() -> None:
    FakeSessionFactory.calls = []
    FakeRunner.instances = []

    status = run_start(
        request=(
            sandbox_request(
                trading_account_id=(
                    None
                )
            )
        ),
        registry=(
            WebRunnerRegistry()
        ),
        account=make_account(),
    )

    assert status == "started"

    assert (
        FakeSessionFactory.calls
        == [
            {
                "token": (
                    "account-token"
                ),
                "sandbox_account_id": (
                    "sbx-broker-1"
                ),
            }
        ]
    )

    runner = (
        FakeRunner.instances[
            -1
        ]
    )

    assert (
        runner
        .kwargs[
            "trading_account_id"
        ]
        == "sandbox-account-1"
    )

    assert (
        runner
        .session_id
        .startswith(
            "tinvest:"
            "sandbox-account-1:"
            "sandbox:"
        )
    )


def test_try_start_real_sandbox_without_sandbox_accounts_raises() -> None:
    FakeSessionFactory.calls = []
    FakeRunner.instances = []

    with pytest.raises(
        ValueError
    ) as exc_info:
        run_start(
            request=(
                sandbox_request(
                    trading_account_id=(
                        None
                    )
                )
            ),
            registry=(
                WebRunnerRegistry()
            ),
            account=make_account(
                enabled=False
            ),
        )

    assert (
        "No enabled SANDBOX"
        in str(
            exc_info.value
        )
    )

    assert (
        FakeSessionFactory.calls
        == []
    )


def test_try_start_real_sandbox_missing_token_raises() -> None:
    FakeSessionFactory.calls = []
    FakeRunner.instances = []

    with pytest.raises(
        ValueError
    ) as exc_info:
        run_start(
            request=(
                sandbox_request()
            ),
            registry=(
                WebRunnerRegistry()
            ),
            account=make_account(),
            token=None,
        )

    assert (
        "Failed to get token"
        in str(
            exc_info.value
        )
    )

    assert (
        "Sandbox account"
        in str(
            exc_info.value
        )
    )

    assert (
        FakeSessionFactory.calls
        == []
    )


def test_try_start_real_sandbox_uniquifies_duplicate_session() -> None:
    FakeSessionFactory.calls = []
    FakeRunner.instances = []

    registry = WebRunnerRegistry()

    first = run_start(
        request=sandbox_request(),
        registry=registry,
        account=make_account(),
    )

    second = run_start(
        request=sandbox_request(),
        registry=registry,
        account=make_account(),
    )

    assert first == "started"
    assert second == "started"

    first_id = (
        FakeRunner.instances[
            0
        ]
        .session_id
    )

    second_id = (
        FakeRunner.instances[
            1
        ]
        .session_id
    )

    assert (
        second_id
        == f"{first_id}#2"
    )

    assert registry.has_session_id(
        first_id
    )

    assert registry.has_session_id(
        second_id
    )
