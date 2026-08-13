import pytest

from application.trading_mode_guard import TradingModeGuard
from config.settings import Settings


def test_live_order_is_blocked_in_sandbox_mode() -> None:
    guard = TradingModeGuard(
        settings=Settings(
            trading_mode="sandbox",
            live_trading_enabled=False,
        )
    )

    with pytest.raises(
        RuntimeError,
        match="TRADING_MODE",
    ):
        guard.ensure_live_order_allowed()


def test_live_order_is_blocked_when_live_switch_disabled() -> None:
    guard = TradingModeGuard(
        settings=Settings(
            trading_mode="live",
            live_trading_enabled=False,
            tinvest_token="token",
            tinvest_live_account_id="account",
        )
    )

    with pytest.raises(
        RuntimeError,
        match="LIVE_TRADING_ENABLED",
    ):
        guard.ensure_live_order_allowed()


def test_live_order_is_allowed_only_with_all_live_settings() -> None:
    guard = TradingModeGuard(
        settings=Settings(
            trading_mode="live",
            live_trading_enabled=True,
            tinvest_token="token",
            tinvest_live_account_id="account",
        )
    )

    guard.ensure_live_order_allowed()
