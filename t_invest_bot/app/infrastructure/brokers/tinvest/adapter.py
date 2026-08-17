from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from application.trading_account_service import (
    TradingAccountCredentials,
)
from domain.trading_account import (
    BrokerType,
    TradingAccountMode,
)
from infrastructure.brokers.base import (
    BrokerAccountInfo,
    BrokerConnectionResult,
    BrokerPortfolioInfo,
)
from infrastructure.tinvest.client_factory import (
    TInvestClientFactory,
)


@dataclass(slots=True)
class TInvestBrokerAdapter:
    @property
    def broker_type(
        self,
    ) -> BrokerType:
        return (
            BrokerType.TINVEST
        )

    def validate_credentials(
        self,
        credentials: TradingAccountCredentials,
    ) -> None:
        token = credentials.get(
            "token"
        )

        if not token:
            raise ValueError(
                "T-Invest token "
                "is required"
            )

    def test_connection(
        self,

        credentials: TradingAccountCredentials,

        broker_account_id: str,

        mode: TradingAccountMode,
    ) -> BrokerConnectionResult:
        try:
            self.validate_credentials(
                credentials
            )

            accounts = (
                self.get_accounts(
                    credentials=(
                        credentials
                    ),

                    mode=mode,
                )
            )

            account_found = any(
                account
                .broker_account_id
                == broker_account_id

                for account
                in accounts
            )

            portfolio = None

            if account_found:
                portfolio = (
                    self.get_portfolio(
                        credentials=(
                            credentials
                        ),

                        broker_account_id=(
                            broker_account_id
                        ),

                        mode=mode,
                    )
                )

            return (
                BrokerConnectionResult(
                    success=True,

                    broker=(
                        BrokerType.TINVEST
                    ),

                    broker_account_id=(
                        broker_account_id
                    ),

                    account_found=(
                        account_found
                    ),

                    accounts=accounts,

                    portfolio=portfolio,

                    error=None,
                )
            )

        except Exception as error:
            return (
                BrokerConnectionResult(
                    success=False,

                    broker=(
                        BrokerType.TINVEST
                    ),

                    broker_account_id=(
                        broker_account_id
                    ),

                    account_found=False,

                    accounts=[],

                    portfolio=None,

                    error=repr(
                        error
                    ),
                )
            )

    def get_accounts(
        self,

        credentials: TradingAccountCredentials,

        mode: TradingAccountMode,
    ) -> list[
        BrokerAccountInfo
    ]:
        self.validate_credentials(
            credentials
        )

        token = (
            credentials.require(
                "token"
            )
        )

        client_factory = (
            TInvestClientFactory(
                token=token,
            )
        )

        if (
            mode
            == TradingAccountMode
            .SANDBOX
        ):
            return (
                self
                ._get_sandbox_accounts(
                    client_factory
                )
            )

        return (
            self._get_live_accounts(
                client_factory
            )
        )

    def get_portfolio(
        self,

        credentials: TradingAccountCredentials,

        broker_account_id: str,

        mode: TradingAccountMode,
    ) -> BrokerPortfolioInfo:
        self.validate_credentials(
            credentials
        )

        token = (
            credentials.require(
                "token"
            )
        )

        client_factory = (
            TInvestClientFactory(
                token=token,
            )
        )

        if (
            mode
            == TradingAccountMode
            .SANDBOX
        ):
            return (
                self
                ._get_sandbox_portfolio(
                    client_factory=(
                        client_factory
                    ),

                    account_id=(
                        broker_account_id
                    ),
                )
            )

        return (
            self._get_live_portfolio(
                client_factory=(
                    client_factory
                ),

                account_id=(
                    broker_account_id
                ),
            )
        )

    def _get_live_accounts(
        self,
        client_factory: TInvestClientFactory,
    ) -> list[
        BrokerAccountInfo
    ]:
        with (
            client_factory
            .create_live_client()
            as client
        ):
            response = (
                client.users
                .get_accounts()
            )

        return [
            BrokerAccountInfo(
                broker_account_id=str(
                    account.id
                ),

                name=(
                    account.name
                    or str(
                        account.id
                    )
                ),

                status=str(
                    account.status
                ),

                account_type=str(
                    account.type
                ),
            )
            for account
            in response.accounts
        ]

    def _get_sandbox_accounts(
        self,
        client_factory: TInvestClientFactory,
    ) -> list[
        BrokerAccountInfo
    ]:
        #
        # Sandbox API также позволяет
        # получить доступные sandbox
        # счета.
        #
        with (
            client_factory
            .create_client()
            as client
        ):
            response = (
                client.sandbox
                .get_sandbox_accounts()
            )

        return [
            BrokerAccountInfo(
                broker_account_id=str(
                    account.id
                ),

                name=(
                    account.name
                    or str(
                        account.id
                    )
                ),

                status=str(
                    account.status
                ),

                account_type=str(
                    account.type
                ),
            )
            for account
            in response.accounts
        ]

    def _get_live_portfolio(
        self,

        client_factory: TInvestClientFactory,

        account_id: str,
    ) -> BrokerPortfolioInfo:
        with (
            client_factory
            .create_live_client()
            as client
        ):
            portfolio = (
                client.operations
                .get_portfolio(
                    account_id=(
                        account_id
                    ),
                )
            )

        cash = (
            self._money_to_decimal(
                getattr(
                    portfolio,
                    "total_amount_currencies",
                    None,
                )
            )
        )

        total_value = (
            self._money_to_decimal(
                getattr(
                    portfolio,
                    "total_amount_portfolio",
                    None,
                )
            )
        )

        positions = getattr(
            portfolio,
            "positions",
            [],
        )

        return (
            BrokerPortfolioInfo(
                cash=cash,

                total_value=(
                    total_value
                ),

                positions_count=len(
                    positions
                ),
            )
        )

    def _get_sandbox_portfolio(
        self,

        client_factory: TInvestClientFactory,

        account_id: str,
    ) -> BrokerPortfolioInfo:
        with (
            client_factory
            .create_client()
            as client
        ):
            portfolio = (
                client.sandbox
                .get_sandbox_portfolio(
                    account_id=(
                        account_id
                    ),
                )
            )

        cash = (
            self._money_to_decimal(
                getattr(
                    portfolio,
                    "total_amount_currencies",
                    None,
                )
            )
        )

        total_value = (
            self._money_to_decimal(
                getattr(
                    portfolio,
                    "total_amount_portfolio",
                    None,
                )
            )
        )

        positions = getattr(
            portfolio,
            "positions",
            [],
        )

        return (
            BrokerPortfolioInfo(
                cash=cash,

                total_value=(
                    total_value
                ),

                positions_count=len(
                    positions
                ),
            )
        )

    @staticmethod
    def _money_to_decimal(
        value,
    ) -> Decimal:
        if value is None:
            return Decimal("0")

        return (
            Decimal(
                str(
                    getattr(
                        value,
                        "units",
                        0,
                    )
                )
            )
            + (
                Decimal(
                    str(
                        getattr(
                            value,
                            "nano",
                            0,
                        )
                    )
                )
                / Decimal(
                    "1000000000"
                )
            )
        )
