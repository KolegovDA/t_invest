import sys

from config import (
    embedded,
)
from config.settings import (
    Settings,
)


_OVERRIDABLE_VARS = [
    "TINVEST_TOKEN",
    "TINVEST_SANDBOX_TOKEN",
    "HEAD_SERVER_URL",
    "HEAD_SERVER_ENABLED",
]


def test_packaged_build_uses_embedded_values(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        sys,
        "frozen",
        True,
        raising=False,
    )

    monkeypatch.setattr(
        "config.settings"
        "._load_dotenv_if_available",
        lambda: None,
    )

    for name in (
        _OVERRIDABLE_VARS
    ):
        monkeypatch.delenv(
            name,
            raising=False,
        )

    settings = (
        Settings
        .from_env()
    )

    # Токены брокера не
    # зашиваются в exe:
    # только env или
    # настройки счёта.
    assert (
        settings
        .tinvest_token
        is None
    )

    assert (
        settings
        .tinvest_sandbox_token
        is None
    )

    assert (
        settings
        .head_server_url
        == embedded
        .EMBEDDED_HEAD_SERVER_URL
    )

    assert (
        settings
        .head_server_enabled
        is True
    )


def test_dev_build_keeps_env_only_defaults(
    monkeypatch,
) -> None:
    assert not (
        hasattr(
            sys,
            "frozen",
        )
    )

    monkeypatch.setattr(
        "config.settings"
        "._load_dotenv_if_available",
        lambda: None,
    )

    for name in (
        _OVERRIDABLE_VARS
    ):
        monkeypatch.delenv(
            name,
            raising=False,
        )

    settings = (
        Settings
        .from_env()
    )

    assert (
        settings
        .head_server_enabled
        is False
    )

    assert (
        settings
        .head_server_url
        is None
    )


def test_env_overrides_embedded_values(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        sys,
        "frozen",
        True,
        raising=False,
    )

    monkeypatch.setattr(
        "config.settings"
        "._load_dotenv_if_available",
        lambda: None,
    )

    for name in (
        _OVERRIDABLE_VARS
    ):
        monkeypatch.delenv(
            name,
            raising=False,
        )

    monkeypatch.setenv(
        "HEAD_SERVER_URL",
        "http://override:9000",
    )

    monkeypatch.setenv(
        "HEAD_SERVER_ENABLED",
        "false",
    )

    settings = (
        Settings
        .from_env()
    )

    assert (
        settings
        .head_server_url
        == "http://override:9000"
    )

    assert (
        settings
        .head_server_enabled
        is False
    )
