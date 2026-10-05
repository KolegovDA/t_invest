from dataclasses import dataclass
from decimal import Decimal

from domain.balance_snapshot import (
    BalanceSnapshot,
)
from infrastructure.sqlite.sqlite_database import (
    SQLiteDatabase,
)


@dataclass(slots=True)
class SQLiteBalanceSnapshotRepository:
    database: SQLiteDatabase

    def record(
        self,
        snapshot: BalanceSnapshot,
    ) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO balance_snapshots (
                    created_at,
                    trading_account_id,
                    currency,
                    equity
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    snapshot.created_at,
                    snapshot.trading_account_id,
                    snapshot.currency,
                    str(
                        snapshot.equity
                    ),
                ),
            )

    def record_if_due(self, snapshot: BalanceSnapshot, interval_seconds: int = 15) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO balance_snapshots (created_at, trading_account_id, currency, equity)
                SELECT ?, ?, ?, ?
                WHERE NOT EXISTS (
                    SELECT 1 FROM balance_snapshots
                    WHERE trading_account_id = ? AND currency = ?
                    AND (julianday(?) - julianday(created_at)) * 86400 < ?
                )
                """,
                (
                    snapshot.created_at, snapshot.trading_account_id,
                    snapshot.currency, str(snapshot.equity),
                    snapshot.trading_account_id, snapshot.currency,
                    snapshot.created_at, interval_seconds,
                ),
            )

    def get_since(
        self,
        since: str,
    ) -> (
        list[BalanceSnapshot]
    ):
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    id,
                    created_at,
                    trading_account_id,
                    currency,
                    equity
                FROM balance_snapshots
                WHERE created_at >= ?
                ORDER BY id ASC
                """,
                (
                    since,
                ),
            ).fetchall()

        return [
            BalanceSnapshot(
                id=int(
                    row[
                        "id"
                    ]
                ),

                created_at=(
                    row[
                        "created_at"
                    ]
                ),

                trading_account_id=(
                    row[
                        "trading_account_id"
                    ]
                ),

                currency=(
                    row[
                        "currency"
                    ]
                ),

                equity=Decimal(
                    row[
                        "equity"
                    ]
                ),
            )

            for row in rows
        ]

    def get_first_by_account(
        self,
        trading_account_id: str,
    ) -> BalanceSnapshot | None:
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT id, created_at, trading_account_id, currency, equity
                FROM balance_snapshots
                WHERE trading_account_id = ?
                ORDER BY julianday(created_at) ASC, id ASC
                LIMIT 1
                """,
                (trading_account_id,),
            ).fetchone()

        if row is None:
            return None

        return BalanceSnapshot(
            id=int(row["id"]),
            created_at=row["created_at"],
            trading_account_id=row["trading_account_id"],
            currency=row["currency"],
            equity=Decimal(row["equity"]),
        )

    def get_first_by_currency(
        self,
    ) -> (
        dict[
            str,
            BalanceSnapshot,
        ]
    ):
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    s.id,
                    s.created_at,
                    s.trading_account_id,
                    s.currency,
                    s.equity
                FROM balance_snapshots s
                JOIN (
                    SELECT MIN(id) AS min_id
                    FROM balance_snapshots
                    GROUP BY currency
                ) m ON s.id = m.min_id
                """
            ).fetchall()

        return {
            row[
                "currency"
            ]: BalanceSnapshot(
                id=int(
                    row[
                        "id"
                    ]
                ),

                created_at=(
                    row[
                        "created_at"
                    ]
                ),

                trading_account_id=(
                    row[
                        "trading_account_id"
                    ]
                ),

                currency=(
                    row[
                        "currency"
                    ]
                ),

                equity=Decimal(
                    row[
                        "equity"
                    ]
                ),
            )

            for row in rows
        }

    def delete_older_than(
        self,
        cutoff: str,
    ) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """
                DELETE FROM balance_snapshots
                WHERE created_at < ?
                """,
                (
                    cutoff,
                ),
            )
