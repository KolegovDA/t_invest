from __future__ import annotations

from dataclasses import dataclass
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from decimal import Decimal

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
from infrastructure.tinvest.client_factory import (
    TInvestClientFactory,
)
from t_tech.invest.grpc.operations import (
    OperationState,
)
from t_tech.invest.schemas import GetOperationsByCursorRequest, OperationType

OPERATIONS_CHUNK_DAYS = 30


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

        token = (
            credentials
            .require(
                "token"
            )
        )

        client_factory = (
            TInvestClientFactory(
                token=token,
            )
        )

        since_utc = (
            self
            ._ensure_utc(
                since
            )
        )

        now = (
            datetime
            .now(
                timezone
                .utc
            )
        )

        if (
            mode
            == TradingAccountMode
            .SANDBOX
        ):
            raw_operations = (
                self
                ._get_sandbox_operations(
                    client_factory=(
                        client_factory
                    ),

                    account_id=(
                        broker_account_id
                    ),

                    from_=(
                        since_utc
                    ),

                    to_=(
                        now
                    ),
                )
            )

        else:
            raw_operations = (
                self
                ._get_live_operations(
                    client_factory=(
                        client_factory
                    ),

                    account_id=(
                        broker_account_id
                    ),

                    from_=(
                        since_utc
                    ),

                    to_=(
                        now
                    ),
                )
            )

        return (
            self
            ._parse_operations(
                operations=(
                    raw_operations
                ),

                currency=(
                    currency
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

    def _get_live_operations(
        self,

        client_factory: TInvestClientFactory,

        account_id: str,

        from_: datetime,

        to_: datetime,
    ) -> list:
        operations = []

        chunk_start = from_

        while (
            chunk_start
            < to_
        ):
            chunk_end = (
                min(
                    chunk_start
                    + timedelta(
                        days=(
                            OPERATIONS_CHUNK_DAYS
                        ),
                    ),

                    to_,
                )
            )

            with (
                client_factory
                .create_live_client()
                as client
            ):
                cursor = ""
                seen_cursors = set()
                while True:
                    response = client.operations.get_operations_by_cursor(
                        GetOperationsByCursorRequest(
                            account_id=account_id, from_=chunk_start, to=chunk_end,
                            cursor=cursor, limit=1000,
                            without_commissions=False, without_trades=False,
                            without_overnights=False,
                        ),
                    )
                    operations.extend(response.items)
                    if not response.has_next:
                        break
                    cursor = response.next_cursor
                    if not cursor or cursor in seen_cursors:
                        raise ValueError("T-Invest operations pagination did not advance")
                    seen_cursors.add(cursor)

            chunk_start = (
                chunk_end
            )

        return operations

    def _get_sandbox_operations(
        self,

        client_factory: TInvestClientFactory,

        account_id: str,

        from_: datetime,

        to_: datetime,
    ) -> list:
        operations = []

        chunk_start = from_

        while (
            chunk_start
            < to_
        ):
            chunk_end = (
                min(
                    chunk_start
                    + timedelta(
                        days=(
                            OPERATIONS_CHUNK_DAYS
                        ),
                    ),

                    to_,
                )
            )

            with (
                client_factory
                .create_client()
                as client
            ):
                response = (
                    client
                    .sandbox
                    .get_sandbox_operations(
                        account_id=(
                            account_id
                        ),

                        from_=(
                            chunk_start
                        ),

                        to=(
                            chunk_end
                        ),
                    )
                )

            operations.extend(
                response
                .operations
            )

            chunk_start = (
                chunk_end
            )

        return operations

    @staticmethod
    def _parse_operations(
        operations: list,

        currency: (
            str | None
        ),
    ) -> list[
        BrokerOperation
    ]:
        parsed = []

        seen_keys = set()

        for operation in operations:
            if not (
                TInvestBrokerAdapter
                ._is_executed(
                    getattr(
                        operation,
                        "state",
                        None,
                    )
                )
            ):
                continue

            operation_currency = (
                str(
                    getattr(
                        operation,
                        "currency",
                        "",
                    )

                    or getattr(getattr(operation, "payment", None), "currency", "")
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
                    operation_currency
                    != (
                        expected_currency
                    )
                ):
                    continue

            payment = (
                TInvestBrokerAdapter
                ._money_to_decimal(
                    getattr(
                        operation,
                        "payment",
                        None,
                    )
                )
            )

            occurred_at = (
                getattr(
                    operation,
                    "date",
                    None,
                )
            )

            if (
                occurred_at
                is None
            ):
                continue

            occurred_at = (
                TInvestBrokerAdapter
                ._ensure_utc(
                    occurred_at
                )
            )

            operation_type = getattr(operation, "operation_type", None)
            raw_type = getattr(operation, "type", "")
            if operation_type is None and isinstance(raw_type, (int, OperationType)):
                operation_type = raw_type
            kind = str(raw_type or "").strip().lower()
            if operation_type is not None:
                try:
                    kind = OperationType(int(operation_type)).name.lower().removeprefix(
                        "operation_type_"
                    ).replace("_", "")
                except (TypeError, ValueError):
                    pass

            if not kind:
                kind = (
                    "unknown"
                )

            operation_id = (
                str(
                    getattr(
                        operation,
                        "id",
                        "",
                    )

                    or ""
                )
            )

            dedup_key = (
                operation_id

                or (
                    f"{kind}"
                    f"|{occurred_at}"
                    f"|{payment}"
                )
            )

            if (
                dedup_key
                in seen_keys
            ):
                continue

            seen_keys.add(
                dedup_key
            )

            parsed.append(
                BrokerOperation(
                    occurred_at=(
                        occurred_at
                    ),

                    kind=kind,

                    payment=(
                        payment
                    ),

                    currency=(
                        operation_currency
                    ),
                    operation_id=operation_id,
                    instrument_id=(
                        getattr(operation, "instrument_uid", None)
                        or getattr(operation, "figi", None)
                    ),
                    ticker=getattr(operation, "ticker", None) or None,
                    quantity=Decimal(str(getattr(operation, "quantity", 0) or 0)),
                )
            )

        parsed.sort(
            key=(
                lambda
                operation: (
                    operation
                    .occurred_at
                )
            ),
        )

        return parsed

    @staticmethod
    def _is_executed(
        state,
    ) -> bool:
        executed = (
            OperationState.OPERATION_STATE_EXECUTED
        )

        if (
            state
            == executed
        ):
            return True

        try:
            state_value = int(
                state
            )

            executed_value = int(
                executed
            )

        except (
            TypeError,

            ValueError,
        ):
            return False

        return (
            state_value
            == executed_value
        )

    @staticmethod
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
