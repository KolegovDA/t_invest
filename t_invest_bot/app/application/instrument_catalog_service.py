from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from application.trading_account_service import TradingAccountService
from config.settings import Settings
from domain.trading_account import BrokerType
from infrastructure.tinvest.client_factory import TInvestClientFactory
from infrastructure.tinvest.instrument_mapper import TInvestInstrumentMapper
from infrastructure.tinvest.instrument_provider import TInvestInstrumentProvider


@dataclass(slots=True)
class InstrumentCatalogItem:
    instrument_uid: str
    ticker: str
    name: str
    currency: str
    lot_size: int
    min_price_step: Decimal


@dataclass(slots=True)
class InstrumentCatalogService:
    settings: Settings
    trading_account_service: TradingAccountService

    def search(
        self,
        query: str,
        trading_account_id: str | None = None,
        limit: int = 50,
    ) -> list[InstrumentCatalogItem]:
        token = self._resolve_token(
            trading_account_id=trading_account_id,
        )

        provider = TInvestInstrumentProvider(
            client_factory=TInvestClientFactory(
                token=token,
            ),
            mapper=TInvestInstrumentMapper(),
        )

        instruments = provider.search_shares(
            query=query,
            limit=limit,
        )

        return [
            InstrumentCatalogItem(
                instrument_uid=instrument.id,
                ticker=instrument.ticker,
                name=instrument.name,
                currency=instrument.currency,
                lot_size=instrument.lot_size,
                min_price_step=instrument.min_price_step,
            )
            for instrument
            in instruments
        ]

    def _resolve_token(
        self,
        trading_account_id: str | None,
    ) -> str:
        if trading_account_id:
            try:
                account = (
                    self.trading_account_service
                    .get(
                        trading_account_id
                    )
                )
            except KeyError as error:
                raise ValueError(
                    "Trading account not found"
                ) from error

            if not account.enabled:
                raise ValueError(
                    "Trading account is disabled"
                )

            if (
                account.broker
                != BrokerType.TINVEST
            ):
                raise ValueError(
                    "Instrument search is currently "
                    "implemented only for T-Invest"
                )

            credentials = (
                self.trading_account_service
                .get_credentials(
                    account.id
                )
            )

            return credentials.require(
                "token"
            )

        token = self.settings.tinvest_token

        if not token:
            raise ValueError(
                "T-Invest token is not configured"
            )

        return token
