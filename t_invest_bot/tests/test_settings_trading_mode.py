import pytest

from config.settings import Settings


def test_settings_accept_sandbox_mode() -> None:
    settings = Settings(
        trading_mode="sandbox",
        tinvest_sandbox_token="sandbox-token",
    )

    settings.validate()

    assert settings.is_sandbox is True
    assert settings.is_live is False


def test_settings_require_live_account() -> None:
    settings = Settings(
        trading_mode="live",
        tinvest_token="production-token",
    )

    with pytest.raises(
        ValueError,
        match="TINVEST_LIVE_ACCOUNT_ID",
    ):
        settings.validate()


def test_settings_accept_live_mode() -> None:
    settings = Settings(
        trading_mode="live",
        tinvest_token="production-token",
        tinvest_live_account_id="account-id",
    )

    settings.validate()

    assert settings.is_live is True
