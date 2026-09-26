import importlib
import os

import infrastructure.tinvest.client_factory as client_factory_module

from infrastructure.tinvest.client_factory import (
    LIVE_TARGET,
    SANDBOX_TARGET,
)


def test_live_and_sandbox_targets_are_different() -> None:
    assert LIVE_TARGET == (
        "invest-public-api.tbank.ru:443"
    )

    assert SANDBOX_TARGET == (
        "sandbox-invest-public-api.tbank.ru:443"
    )

    assert LIVE_TARGET != SANDBOX_TARGET


def test_ssl_tbank_verify_enabled_by_default() -> None:
    assert os.environ.get(
        "SSL_TBANK_VERIFY",
        "",
    ).lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def test_ssl_tbank_verify_respects_explicit_value(
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "SSL_TBANK_VERIFY",
        "false",
    )

    importlib.reload(
        client_factory_module,
    )

    assert (
        os.environ["SSL_TBANK_VERIFY"]
        == "false"
    )

    importlib.reload(
        client_factory_module,
    )
