from __future__ import annotations

from dataclasses import dataclass
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from decimal import (
    Decimal,
)

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
from infrastructure.brokers.base import (
    BrokerAccountInfo,
    BrokerConnectionResult,
    BrokerPortfolioInfo,
)
from infrastructure.bybit.client import (
    LIVE_BASE_URL,
    TESTNET_BASE_URL,
    BybitClient,
    to_decimal,
)

UNIFIED_ACCOUNT_ID = (
    "UNIFIED"
)

SETTLEMENT_COINS = (
    "USDT",

    "USDC",

    "USD",
)


def _ensure_utc(
    value: datetime,
) -> datetime:
    if (
        value
        .tzinfo
        is None
    ):
        return (
            value
            .replace(
                tzinfo=(
                    timezone
                    .utc
                ),
            )
        )

    return value


def _ms_to_datetime(
    value,
) -> (
    datetime
    | None
):
    if (
        value
        is None
    ):
        return None

    try:
        ms = int(
            value
        )

    except (
        TypeError,

        ValueError,
    ):
        return None

    return (
        datetime
        .fromtimestamp(
            ms
            / 1000,

            tz=(
                timezone
                .utc
            ),
        )
    )


@dataclass(slots=True)
class BybitBrokerAdapter:
    @property
    def broker_type(
        self,
    ) -> BrokerType:
        return (
            BrokerType.BYBIT
        )

    def validate_credentials(
        self,
        credentials: TradingAccountCredentials,
    ) -> None:
        api_key = (
            credentials
            .get(
                "api_key"
            )
        )

        api_secret = (
            credentials
            .get(
                "api_secret"
            )
        )

        if (
            not api_key
            or not api_secret
        ):
            raise ValueError(
                "Bybit API key "
                "and API secret "
                "are required"
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
                        BrokerType
                        .BYBIT
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
                        BrokerType
                        .BYBIT
                    ),

                    broker_account_id=(
                        broker_account_id
                    ),

                    account_found=(
                        False
                    ),

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

        client = (
            self._build_client(
                credentials=(
                    credentials
                ),

                mode=mode,
            )
        )

        entry = (
            client
            .get_wallet_balance()
        )

        return [
            self
            ._wallet_entry_to_account(
                entry
            )
        ]

    def get_portfolio(
        self,

        credentials: TradingAccountCredentials,

        broker_account_id: str,

        mode: TradingAccountMode,
    ) -> BrokerPortfolioInfo:
        self.validate_credentials(
            credentials
        )

        client = (
            self._build_client(
                credentials=(
                    credentials
                ),

                mode=mode,
            )
        )

        entry = (
            client
            .get_wallet_balance()
        )

        return (
            self
            ._wallet_entry_to_portfolio(
                entry
            )
        )

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
        self.validate_credentials(
            credentials
        )

        client = (
            self._build_client(
                credentials=(
                    credentials
                ),

                mode=mode,
            )
        )

        since_utc = (
            _ensure_utc(
                since
            )
        )

        entries = []
        chunk_start = since_utc
        now = datetime.now(timezone.utc)
        while chunk_start < now:
            chunk_end = min(chunk_start + timedelta(days=7), now)
            entries.extend(client.get_transaction_log(
                start_time=int(chunk_start.timestamp() * 1000),
                end_time=int(chunk_end.timestamp() * 1000) - 1,
            ))
            chunk_start = chunk_end

        operations = []

        for entry in entries:
            payment = (
                to_decimal(
                    entry
                    .get(
                        "change"
                    )
                )
            )

            entry_currency = (
                str(
                    entry
                    .get(
                        "currency"
                    )

                    or ""
                )
                .strip()
                .upper()
            )

            if currency:
                expected_currency = (
                    currency
                    .strip()
                    .upper()
                )

                if (
                    entry_currency
                    != (
                        expected_currency
                    )
                ):
                    continue

            occurred_at = (
                _ms_to_datetime(
                    entry
                    .get(
                        "transactionTime"
                    )
                )
            )

            if (
                occurred_at
                is None
            ):
                continue

            kind = (
                str(
                    entry
                    .get(
                        "type"
                    )

                    or ""
                )
                .strip()
                .lower()
            )

            if not kind:
                kind = (
                    "unknown"
                )

            operations.append(
                BrokerOperation(
                    occurred_at=(
                        occurred_at
                    ),

                    kind=kind,

                    payment=(
                        payment
                    ),

                    currency=(
                        entry_currency
                    ),
                    operation_id=str(entry.get("id") or ""),
                    ticker=str(entry.get("symbol") or "") or None,
                    quantity=to_decimal(entry.get("qty")) if entry.get("qty") is not None else None,
                )
            )

        operations.sort(
            key=(
                lambda
                operation: (
                    operation
                    .occurred_at
                )
            ),
        )

        return operations

    def asset_rules(self, credentials: TradingAccountCredentials, symbol: str) -> dict:
        client = self._build_client(credentials, TradingAccountMode.LIVE)
        instruments = client.get_instruments_info(symbol=symbol)
        fees = client.get_fee_rates(symbol)
        if not instruments or not fees:
            raise ValueError(f"Bybit rules or account fees not found: {symbol}")
        instrument = instruments[0]
        lot = instrument.get("lotSizeFilter") or {}
        fee = fees[0]
        return {
            "symbol": symbol.upper(),
            "base_coin": instrument.get("baseCoin"),
            "quote_coin": instrument.get("quoteCoin"),
            "min_order_amount": str(to_decimal(lot.get("minOrderAmt"))),
            "quantity_step": str(to_decimal(lot.get("basePrecision"))),
            "min_quantity": str(to_decimal(lot.get("minOrderQty"))),
            "price_step": str(to_decimal((instrument.get("priceFilter") or {}).get("tickSize"))),
            "maker_percent": str(to_decimal(fee.get("makerFeeRate")) * 100),
            "taker_percent": str(to_decimal(fee.get("takerFeeRate")) * 100),
        }

    def _build_client(
        self,

        credentials: TradingAccountCredentials,

        mode: TradingAccountMode,
    ) -> BybitClient:
        base_url = (
            TESTNET_BASE_URL
        )

        if (
            mode
            == TradingAccountMode
            .LIVE
        ):
            base_url = (
                LIVE_BASE_URL
            )

        return BybitClient(
            api_key=(
                credentials
                .require(
                    "api_key"
                )
            ),

            api_secret=(
                credentials
                .require(
                    "api_secret"
                )
            ),

            base_url=(
                base_url
            ),
        )

    @staticmethod
    def _wallet_entry_to_account(
        entry: dict,
    ) -> (
        BrokerAccountInfo
    ):
        return (
            BrokerAccountInfo(
                broker_account_id=(
                    UNIFIED_ACCOUNT_ID
                ),

                name=(
                    "Bybit "
                    "Unified "
                    "Trading "
                    "Account"
                ),

                status=(
                    "active"
                ),

                account_type=(
                    "unified"
                ),
            )
        )

    @staticmethod
    def _wallet_entry_to_portfolio(
        entry: dict,
    ) -> (
        BrokerPortfolioInfo
    ):
        coins = (
            entry
            .get("coin")
            or []
        )

        cash = (
            Decimal("0")
        )

        positions_count = 0

        for coin in coins:
            coin_name = (
                str(
                    coin
                    .get(
                        "coin"
                    )

                    or ""
                )
                .upper()
            )

            wallet_balance = (
                to_decimal(
                    coin
                    .get(
                        "walletBalance"
                    )
                )
            )

            if (
                coin_name
                in SETTLEMENT_COINS
            ):
                cash = (
                    cash
                    + wallet_balance
                )

                continue

            if (
                wallet_balance
                != Decimal("0")
            ):
                positions_count = (
                    positions_count
                    + 1
                )

        total_value = (
            to_decimal(
                entry
                .get(
                    "totalEquity"
                )
            )
        )

        if (
            total_value
            == Decimal("0")
        ):
            total_value = (
                to_decimal(
                    entry
                    .get(
                        "totalWallet"
                        "Balance"
                    )
                )
            )

        return (
            BrokerPortfolioInfo(
                cash=cash,

                total_value=(
                    total_value
                ),

                positions_count=(
                    positions_count
                ),
            )
        )
