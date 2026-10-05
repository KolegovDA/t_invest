import hashlib
import json
from dataclasses import dataclass
from datetime import datetime

from domain.broker_operation import BrokerOperation
from decimal import (
    Decimal,
)

from domain.broker_cash_flow import (
    BrokerCashFlow,
)
from infrastructure.sqlite.sqlite_database import (
    SQLiteDatabase,
)


@dataclass(slots=True)
class SQLiteBrokerCashFlowRepository:
    database: SQLiteDatabase

    def record(
        self,
        flow: BrokerCashFlow,
    ) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO broker_cash_flows (
                    trading_account_id,
                    occurred_at,
                    kind,
                    currency,
                    payment
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    flow.trading_account_id,
                    flow.occurred_at,
                    flow.kind,
                    flow.currency,
                    str(
                        flow.payment
                    ),
                ),
            )

    def get_since(
        self,
        since: str,
    ) -> (
        list[BrokerCashFlow]
    ):
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    id,
                    trading_account_id,
                    occurred_at,
                    kind,
                    currency,
                    payment
                FROM broker_cash_flows
                WHERE occurred_at >= ?
                ORDER BY occurred_at ASC, id ASC
                """,
                (
                    since,
                ),
            ).fetchall()

        return [
            BrokerCashFlow(
                id=int(
                    row[
                        "id"
                    ]
                ),

                trading_account_id=(
                    row[
                        "trading_account_id"
                    ]
                ),

                occurred_at=(
                    row[
                        "occurred_at"
                    ]
                ),

                kind=(
                    row[
                        "kind"
                    ]
                ),

                currency=(
                    row[
                        "currency"
                    ]
                ),

                payment=Decimal(
                    row[
                        "payment"
                    ]
                ),
            )

            for row in rows
        ]

    def record_operation(
        self,
        trading_account_id: str,
        operation: BrokerOperation,
    ) -> None:
        operation_id = operation.operation_id or hashlib.sha256(
            json.dumps([
                operation.occurred_at.isoformat(), operation.kind,
                operation.currency, str(operation.payment),
                operation.instrument_id, operation.ticker,
                str(operation.quantity),
            ], ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO broker_operations (
                    trading_account_id, operation_id, occurred_at, kind,
                    currency, payment, instrument_id, ticker, quantity
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trading_account_id, operation_id,
                    operation.occurred_at.isoformat(), operation.kind,
                    operation.currency, str(operation.payment),
                    operation.instrument_id, operation.ticker,
                    str(operation.quantity) if operation.quantity is not None else None,
                ),
            )

    def operations_since(self, since: str) -> list[tuple[str, BrokerOperation]]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM broker_operations
                WHERE occurred_at >= ?
                ORDER BY occurred_at ASC, operation_id ASC
                """,
                (since,),
            ).fetchall()
        return [
            (
                row["trading_account_id"],
                BrokerOperation(
                    occurred_at=datetime.fromisoformat(row["occurred_at"]),
                    kind=row["kind"], currency=row["currency"],
                    payment=Decimal(row["payment"]),
                    operation_id=row["operation_id"],
                    instrument_id=row["instrument_id"], ticker=row["ticker"],
                    quantity=Decimal(row["quantity"]) if row["quantity"] is not None else None,
                ),
            )
            for row in rows
        ]

    def sync_state(self, trading_account_id: str) -> tuple[str, str] | None:
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT covered_since, synced_at FROM broker_operation_sync
                WHERE trading_account_id = ?
                """,
                (trading_account_id,),
            ).fetchone()
        return (row["covered_since"], row["synced_at"]) if row is not None else None

    def mark_synced(
        self, trading_account_id: str, covered_since: str, synced_at: str,
    ) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO broker_operation_sync (trading_account_id, covered_since, synced_at)
                VALUES (?, ?, ?)
                ON CONFLICT(trading_account_id) DO UPDATE SET
                    covered_since = MIN(covered_since, excluded.covered_since),
                    synced_at = excluded.synced_at
                """,
                (trading_account_id, covered_since, synced_at),
            )

    def last_occurred_at(
        self,
        trading_account_id: str,
    ) -> (
        str | None
    ):
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT occurred_at
                FROM broker_cash_flows
                WHERE trading_account_id = ?
                ORDER BY occurred_at DESC, id DESC
                LIMIT 1
                """,
                (
                    trading_account_id,
                ),
            ).fetchone()

        if row is None:
            return None

        return (
            row[
                "occurred_at"
            ]
        )
