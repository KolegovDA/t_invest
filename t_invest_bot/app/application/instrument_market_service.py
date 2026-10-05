from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from application.auto_portfolio_selector import (
    InstrumentMarketSnapshot,
)
from application.trading_account_service import (
    TradingAccountService,
    PlatformCredentialsProvider,
)
from config.settings import Settings
from domain.trading_account import (
    BrokerType,
)
from infrastructure.tinvest.candles_mapper import (
    TInvestCandlesMapper,
)
from infrastructure.tinvest.client_factory import (
    TInvestClientFactory,
)
from infrastructure.tinvest.history_provider import (
    TInvestHistoryProvider,
)
from infrastructure.tinvest.instrument_mapper import (
    TInvestInstrumentMapper,
)
from infrastructure.tinvest.instrument_provider import (
    TInvestInstrumentProvider,
)
from strategy.risk_score import (
    RiskScoreCalculator,
)


@dataclass(slots=True)
class InstrumentMarketService:
    """
    Рыночные снимки для
    выбора инструментов:
    цена и волатильность
    по дневным свечам
    за 90 дней.
    """

    settings: Settings

    trading_account_service: (
        TradingAccountService
    )

    history_days: int = 90

    platform_connection_service: PlatformCredentialsProvider | None = None

    def get_snapshots(
        self,
        tickers: list[str],
        trading_account_id: (
            str | None
        ) = None,
    ) -> list[
        InstrumentMarketSnapshot
    ]:
        wanted = {
            ticker
            .strip()
            .upper()

            for ticker
            in tickers

            if ticker.strip()
        }

        if not wanted:
            return []

        token = (
            self
            ._resolve_token(
                trading_account_id=(
                    trading_account_id
                ),
            )
        )

        client_factory = (
            TInvestClientFactory(
                token=token,
            )
        )

        provider = (
            TInvestInstrumentProvider(
                client_factory=(
                    client_factory
                ),

                mapper=(
                    TInvestInstrumentMapper()
                ),
            )
        )

        history = (
            TInvestHistoryProvider(
                client_factory=(
                    client_factory
                ),

                mapper=(
                    TInvestCandlesMapper()
                ),
            )
        )

        shares = [
            instrument

            for instrument
            in (
                provider
                .get_shares()
            )

            if (
                instrument
                .ticker
                .upper()

                in wanted
            )

            and (
                instrument
                .currency
                == "RUB"
            )
        ]

        date_to = (
            datetime.now()
        )

        date_from = (
            date_to
            - timedelta(
                days=(
                    self
                    .history_days
                ),
            )
        )

        risk_calculator = (
            RiskScoreCalculator()
        )

        snapshots = []

        for share in shares:
            candles = (
                history
                .get_daily_candles(
                    instrument_id=(
                        share.id
                    ),

                    date_from=(
                        date_from
                    ),

                    date_to=(
                        date_to
                    ),
                )
            )

            if (
                len(candles)
                < 2
            ):
                continue

            risk_score = (
                risk_calculator
                .calculate(
                    instrument_id=(
                        share.id
                    ),

                    candles=(
                        candles
                    ),
                )
            )

            snapshots.append(
                InstrumentMarketSnapshot(
                    instrument_uid=(
                        share.id
                    ),

                    ticker=(
                        share
                        .ticker
                        .upper()
                    ),

                    name=(
                        share
                        .name
                    ),

                    currency=(
                        share
                        .currency
                    ),

                    lot_size=(
                        share
                        .lot_size
                    ),

                    price=(
                        candles[
                            -1
                        ]
                        .close
                    ),

                    volatility_percent=(
                        risk_score
                        .volatility_percent
                    ),

                    risk_value=(
                        risk_score
                        .value
                    ),

                    risk_band=(
                        risk_score
                        .band
                    ),
                )
            )

        return snapshots

    def _resolve_token(
        self,
        trading_account_id: (
            str | None
        ),
    ) -> str:
        if trading_account_id:
            try:
                account = (
                    self
                    .trading_account_service
                    .get(
                        trading_account_id
                    )
                )

            except KeyError as error:
                raise ValueError(
                    "Trading account "
                    "not found"
                ) from error

            if (
                not account
                .enabled
            ):
                raise ValueError(
                    "Trading account "
                    "is disabled"
                )

            if (
                account.broker
                != BrokerType
                .TINVEST
            ):
                raise ValueError(
                    "Instrument market "
                    "data is currently "
                    "implemented only "
                    "for T-Invest"
                )

            credentials = (
                self
                .trading_account_service
                .get_credentials(
                    account.id
                )
            )

            return (
                credentials
                .require(
                    "token"
                )
            )

        if self.platform_connection_service is not None:
            platforms = sorted(
                self.platform_connection_service.get_all(),
                key=lambda platform: platform.mode.value != "live",
            )
            for platform in platforms:
                if platform.broker == BrokerType.TINVEST:
                    token = self.platform_connection_service.get_credentials(platform.id).get("token")
                    if token:
                        return token

        for account in self.trading_account_service.get_enabled():
            if account.broker == BrokerType.TINVEST:
                token = self.trading_account_service.get_credentials(account.id).get("token")
                if token:
                    return token

        token = (
            self
            .settings
            .tinvest_sandbox_token

            or (
                self
                .settings
                .tinvest_token
            )
        )

        if not token:
            raise ValueError(
                "T-Invest token is "
                "not configured"
            )

        return token
