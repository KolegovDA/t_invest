from dataclasses import dataclass

from config.settings import Settings


@dataclass(slots=True)
class TradingModeGuard:
    settings: Settings

    def ensure_live_order_allowed(self) -> None:
        if not self.settings.is_live:
            raise RuntimeError(
                "Live order rejected: TRADING_MODE is not live"
            )

        if not self.settings.live_trading_enabled:
            raise RuntimeError(
                "Live order rejected: LIVE_TRADING_ENABLED is disabled"
            )

        if not self.settings.tinvest_live_account_id:
            raise RuntimeError(
                "Live order rejected: live account ID is not configured"
            )

        if not self.settings.tinvest_token:
            raise RuntimeError(
                "Live order rejected: production token is not configured"
            )
