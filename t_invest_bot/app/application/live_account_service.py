from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from config.settings import Settings
from infrastructure.tinvest.client_factory import (
    TInvestClientFactory,
)


@dataclass(slots=True)
class LiveAccountInfo:
    account_id: str
    name: str
    status: str
    account_type: str
    selected: bool


@dataclass(slots=True)
class LivePortfolioInfo:
    total_amount_shares: Decimal
    total_amount_bonds: Decimal
    total_amount_etf: Decimal
    total_amount_currencies: Decimal
    expected_yield: Decimal
    positions_count: int


@dataclass(slots=True)
class LiveAccountStatus:
    token_configured: bool
    selected_account_id: str | None
    account_found: bool
    live_trading_enabled: bool
    trading_mode: str

    accounts: list[LiveAccountInfo]
    portfolio: LivePortfolioInfo | None

    unary_limits_count: int
    stream_limits_count: int

    error: str | None = None


@dataclass(slots=True)
class LiveAccountService:
    settings: Settings

    def get_status(self) -> LiveAccountStatus:
        token = self.settings.tinvest_token

        if not token:
            return LiveAccountStatus(
                token_configured=False,
                selected_account_id=(
                    self.settings.tinvest_live_account_id
                ),
                account_found=False,
                live_trading_enabled=(
                    self.settings.live_trading_enabled
                ),
                trading_mode=self.settings.trading_mode,
                accounts=[],
                portfolio=None,
                unary_limits_count=0,
                stream_limits_count=0,
                error="TINVEST_TOKEN is not configured",
            )

        try:
            client_factory = TInvestClientFactory(
                token=token,
            )

            with client_factory.create_live_client() as client:
                accounts_response = (
                    client.users.get_accounts()
                )

                accounts: list[LiveAccountInfo] = []

                selected_account = None

                for account in accounts_response.accounts:
                    selected = (
                        account.id
                        == self.settings.tinvest_live_account_id
                    )

                    accounts.append(
                        LiveAccountInfo(
                            account_id=account.id,
                            name=str(
                                getattr(
                                    account,
                                    "name",
                                    "",
                                )
                            ),
                            status=str(
                                getattr(
                                    account,
                                    "status",
                                    "",
                                )
                            ),
                            account_type=str(
                                getattr(
                                    account,
                                    "type",
                                    "",
                                )
                            ),
                            selected=selected,
                        )
                    )

                    if selected:
                        selected_account = account

                portfolio = None

                if selected_account is not None:
                    response = (
                        client.operations.get_portfolio(
                            account_id=selected_account.id,
                        )
                    )

                    portfolio = LivePortfolioInfo(
                        total_amount_shares=self._money(
                            response.total_amount_shares
                        ),
                        total_amount_bonds=self._money(
                            response.total_amount_bonds
                        ),
                        total_amount_etf=self._money(
                            response.total_amount_etf
                        ),
                        total_amount_currencies=self._money(
                            response.total_amount_currencies
                        ),
                        expected_yield=self._quotation(
                            response.expected_yield
                        ),
                        positions_count=len(
                            response.positions
                        ),
                    )

                tariff = client.users.get_user_tariff()

                return LiveAccountStatus(
                    token_configured=True,
                    selected_account_id=(
                        self.settings.tinvest_live_account_id
                    ),
                    account_found=(
                        selected_account is not None
                    ),
                    live_trading_enabled=(
                        self.settings.live_trading_enabled
                    ),
                    trading_mode=(
                        self.settings.trading_mode
                    ),
                    accounts=accounts,
                    portfolio=portfolio,
                    unary_limits_count=len(
                        tariff.unary_limits
                    ),
                    stream_limits_count=len(
                        tariff.stream_limits
                    ),
                    error=None,
                )

        except Exception as error:
            return LiveAccountStatus(
                token_configured=True,
                selected_account_id=(
                    self.settings.tinvest_live_account_id
                ),
                account_found=False,
                live_trading_enabled=(
                    self.settings.live_trading_enabled
                ),
                trading_mode=self.settings.trading_mode,
                accounts=[],
                portfolio=None,
                unary_limits_count=0,
                stream_limits_count=0,
                error=repr(error),
            )

    def _money(
        self,
        value: Any,
    ) -> Decimal:
        if value is None:
            return Decimal("0")

        return (
            Decimal(str(value.units))
            + Decimal(str(value.nano))
            / Decimal("1000000000")
        )

    def _quotation(
        self,
        value: Any,
    ) -> Decimal:
        if value is None:
            return Decimal("0")

        return (
            Decimal(str(value.units))
            + Decimal(str(value.nano))
            / Decimal("1000000000")
        )
