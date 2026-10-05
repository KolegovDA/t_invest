from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol, runtime_checkable

from application.trading_account_service import (
    TradingAccountCredentials,
)
from domain.broker_operation import (
    BrokerOperation,
)
from domain.trading_account import (
    BrokerType,
    TradingAccountMode,
)


@dataclass(slots=True)
class BrokerAccountInfo:
    broker_account_id: str
    name: str

    status: str = ""
    account_type: str = ""


@dataclass(slots=True)
class BrokerPortfolioInfo:
    cash: Decimal

    total_value: Decimal | None = None

    positions_count: int = 0


@dataclass(slots=True)
class BrokerConnectionResult:
    success: bool

    broker: BrokerType

    broker_account_id: (
        str | None
    ) = None

    account_found: bool = False

    accounts: list[
        BrokerAccountInfo
    ] | None = None

    portfolio: (
        BrokerPortfolioInfo | None
    ) = None

    error: str | None = None


@runtime_checkable
class AssetRulesProvider(Protocol):
    def asset_rules(
        self,
        credentials: TradingAccountCredentials,
        symbol: str,
    ) -> dict:
        ...


class BrokerAdapter(
    Protocol
):
    @property
    def broker_type(
        self,
    ) -> BrokerType:
        ...

    def validate_credentials(
        self,
        credentials: TradingAccountCredentials,
    ) -> None:
        ...

    def test_connection(
        self,

        credentials: TradingAccountCredentials,

        broker_account_id: str,

        mode: TradingAccountMode,
    ) -> BrokerConnectionResult:
        ...

    def get_accounts(
        self,

        credentials: TradingAccountCredentials,

        mode: TradingAccountMode,
    ) -> list[
        BrokerAccountInfo
    ]:
        ...

    def get_portfolio(
        self,

        credentials: TradingAccountCredentials,

        broker_account_id: str,

        mode: TradingAccountMode,
    ) -> BrokerPortfolioInfo:
        ...

    def get_operations(
        self,

        credentials: TradingAccountCredentials,

        broker_account_id: str,

        mode: TradingAccountMode,

        since: datetime,

        currency: (
            str | None
        ) = None,
    ) -> list[
        BrokerOperation
    ]:
        ...
