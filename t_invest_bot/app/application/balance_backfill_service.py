from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from domain.balance_snapshot import BalanceSnapshot
from domain.broker_cash_flow import BrokerCashFlow

BACKFILL_DAYS = 180

TINVEST_EXTERNAL_FLOW_KINDS = (
    "input", "output", "inputswift", "outputswift", "inputacquiring",
    "outputacquiring", "outputpenalty", "inpmulti", "outmulti",
    "transiisbs", "transbsbs",
)

BYBIT_EXTERNAL_FLOW_KINDS = ("deposit", "withdrawal")

EXTERNAL_FLOW_KINDS = (*TINVEST_EXTERNAL_FLOW_KINDS, *BYBIT_EXTERNAL_FLOW_KINDS)


@dataclass(slots=True)
class BalanceBackfillService:
    snapshot_repository: Any | None = None
    backfill_repository: Any | None = None
    broker_cash_flow_repository: Any | None = None

    def backfill_account(
        self,
        account: Any,
        adapter: Any,
        credentials: Any,
        currency: str,
        days: int = BACKFILL_DAYS,
    ) -> bool:
        now = datetime.now(timezone.utc)
        since = now - timedelta(days=days)
        repository = self.broker_cash_flow_repository
        if repository is None:
            return False
        state = repository.sync_state(account.id)
        if state is not None and datetime.fromisoformat(state[0]) <= since:
            first_snapshot = (
                self.snapshot_repository.get_first_by_account(account.id)
                if self.snapshot_repository is not None else None
            )
            if first_snapshot is not None and datetime.fromisoformat(first_snapshot.created_at) <= since:
                return False

        portfolio = adapter.get_portfolio(
            credentials=credentials,
            broker_account_id=account.broker_account_id,
            mode=account.mode,
        )
        operations = adapter.get_operations(
            credentials=credentials,
            broker_account_id=account.broker_account_id,
            mode=account.mode,
            since=since,
            currency=None,
        )
        for operation in operations:
            repository.record_operation(account.id, operation)
            if operation.kind in EXTERNAL_FLOW_KINDS:
                repository.record(BrokerCashFlow(
                    trading_account_id=account.id,
                    occurred_at=operation.occurred_at.isoformat(),
                    kind=operation.kind,
                    currency=operation.currency or currency,
                    payment=operation.payment,
                ))

        if self.snapshot_repository is not None:
            self.snapshot_repository.record(BalanceSnapshot(
                created_at=now.isoformat(),
                trading_account_id=account.id,
                currency=currency,
                equity=portfolio.total_value if portfolio.total_value is not None else portfolio.cash,
            ))
        repository.mark_synced(account.id, since.isoformat(), now.isoformat())
        if self.backfill_repository is not None:
            self.backfill_repository.mark_done(account.id, now.isoformat())
        return True
