import json

from dataclasses import (
    dataclass,
)
from datetime import (
    datetime,
    timezone,
)
from decimal import (
    Decimal,
    ROUND_HALF_UP,
)

from infrastructure.sqlite.sqlite_database import (
    SQLiteDatabase,
)


MONEY_QUANT = (
    Decimal("0.01")
)


def quantize_money(
    value: Decimal,
) -> Decimal:
    return (
        value
        .quantize(
            MONEY_QUANT,

            rounding=(
                ROUND_HALF_UP
            ),
        )
    )


@dataclass(slots=True)
class CommissionCharge:
    id: int
    created_at: str
    trading_account_id: (
        str | None
    )
    broker: str
    instrument_id: (
        str | None
    )
    ticker: (
        str | None
    )
    level_index: (
        int | None
    )
    trade_profit: Decimal
    percent: Decimal
    amount: Decimal
    balance_after: Decimal
    synced_with_head: bool

    def to_dict(
        self,
    ) -> dict:
        return {
            "id": (
                self.id
            ),

            "created_at": (
                self
                .created_at
            ),

            "trading_account_id": (
                self
                .trading_account_id
            ),

            "broker": (
                self.broker
            ),

            "instrument_id": (
                self
                .instrument_id
            ),

            "ticker": (
                self.ticker
            ),

            "level_index": (
                self
                .level_index
            ),

            "trade_profit": (
                str(
                    self
                    .trade_profit
                )
            ),

            "percent": (
                str(
                    self
                    .percent
                )
            ),

            "amount": (
                str(
                    self
                    .amount
                )
            ),

            "balance_after": (
                str(
                    self
                    .balance_after
                )
            ),
        }


def _row_to_charge(
    row,
) -> CommissionCharge:
    return CommissionCharge(
        id=int(
            row[
                "id"
            ]
        ),

        created_at=str(
            row[
                "created_at"
            ]
        ),

        trading_account_id=(
            row[
                "trading_account_id"
            ]
        ),

        broker=str(
            row[
                "broker"
            ]
        ),

        instrument_id=(
            row[
                "instrument_id"
            ]
        ),

        ticker=(
            row[
                "ticker"
            ]
        ),

        level_index=(
            int(
                row[
                    "level_index"
                ]
            )

            if (
                row[
                    "level_index"
                ]
                is not None
            )

            else None
        ),

        trade_profit=Decimal(
            row[
                "trade_profit"
            ]
        ),

        percent=Decimal(
            row[
                "percent"
            ]
        ),

        amount=Decimal(
            row[
                "amount"
            ]
        ),

        balance_after=Decimal(
            row[
                "balance_after"
            ]
        ),

        synced_with_head=bool(
            row[
                "synced_with_head"
            ]
        ),
    )


@dataclass(slots=True)
class SQLiteCommissionRepository:
    database: SQLiteDatabase

    def insert_charge(
        self,
        trading_account_id: (
            str | None
        ),
        broker: str,
        instrument_id: (
            str | None
        ),
        ticker: (
            str | None
        ),
        level_index: (
            int | None
        ),
        trade_profit: Decimal,
        percent: Decimal,
        amount: Decimal,
        synced_with_head: bool = (
            False
        ),
    ) -> CommissionCharge:
        cabinet_balance = self.authoritative_balance()
        balance_after = (cabinet_balance if cabinet_balance is not None else self.get_balance()) - amount

        created_at = (
            datetime
            .now(
                timezone.utc
            )
            .isoformat()
        )

        with self.database.connect() as connection:
            cursor = (
                connection
                .execute(
                    """
                    INSERT INTO commission_charges (
                        created_at,
                        trading_account_id,
                        broker,
                        instrument_id,
                        ticker,
                        level_index,
                        trade_profit,
                        percent,
                        amount,
                        balance_after,
                        synced_with_head
                    )
                    VALUES (
                        ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?
                    )
                    """,
                    (
                        created_at,
                        trading_account_id,
                        broker,
                        instrument_id,
                        ticker,
                        level_index,
                        str(
                            trade_profit
                        ),
                        str(
                            percent
                        ),
                        str(
                            amount
                        ),
                        str(
                            balance_after
                        ),
                        1
                        if (
                            synced_with_head
                        )

                        else 0,
                    ),
                )
            )

        if cursor.lastrowid is None:
            raise RuntimeError("Commission charge was not inserted")
        return CommissionCharge(
            id=int(
                cursor.lastrowid
            ),

            created_at=(
                created_at
            ),

            trading_account_id=(
                trading_account_id
            ),

            broker=broker,

            instrument_id=(
                instrument_id
            ),

            ticker=ticker,

            level_index=(
                level_index
            ),

            trade_profit=(
                trade_profit
            ),

            percent=percent,

            amount=amount,

            balance_after=(
                balance_after
            ),

            synced_with_head=(
                synced_with_head
            ),
        )

    def get_balance(
        self,
    ) -> Decimal:
        with self.database.connect() as connection:
            row = (
                connection
                .execute(
                    """
                    SELECT
                        COALESCE(
                            SUM(amount),
                            0
                        )
                        AS total
                    FROM commission_charges
                    """
                )
                .fetchone()
            )

        charged = (
            Decimal(
                str(
                    row[
                        "total"
                    ]
                )
            )
        )

        return (
            quantize_money(
                Decimal("0")
                - charged
            )
        )

    def recent(
        self,
        limit: int = 50,
    ) -> (
        list[
            CommissionCharge
        ]
    ):
        with self.database.connect() as connection:
            rows = (
                connection
                .execute(
                    """
                    SELECT *
                    FROM commission_charges
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (
                        limit,
                    ),
                )
                .fetchall()
            )

        return [
            _row_to_charge(
                row
            )

            for row
            in rows
        ]

    def pending_unsynced(
        self,
        limit: int = 200,
    ) -> (
        list[
            CommissionCharge
        ]
    ):
        with self.database.connect() as connection:
            rows = (
                connection
                .execute(
                    """
                    SELECT *
                    FROM commission_charges
                    WHERE synced_with_head = 0
                    ORDER BY id ASC
                    LIMIT ?
                    """,
                    (
                        limit,
                    ),
                )
                .fetchall()
            )

        return [
            _row_to_charge(
                row
            )

            for row
            in rows
        ]

    def mark_synced(
        self,
        charge_ids: (
            list[int]
        ),
    ) -> None:
        if not charge_ids:
            return

        placeholders = (
            ", ".join(
                "?"
                for _ in (
                    charge_ids
                )
            )
        )

        with self.database.connect() as connection:
            connection.execute(
                f"""
                UPDATE commission_charges
                SET synced_with_head = 1
                WHERE id IN (
                    {placeholders}
                )
                """,
                tuple(
                    charge_ids
                ),
            )

    def save_entitlements(self, payload: dict) -> None:
        balance = Decimal(str(payload["balance"]))
        if not balance.is_finite():
            raise ValueError("Invalid cabinet balance")
        payload = dict(payload)
        with self.database.connect() as connection:
            previous = connection.execute("SELECT payload_json FROM cabinet_entitlements WHERE id = 1").fetchone()
            if previous is not None and json.loads(previous["payload_json"]).get("trial_active") is False:
                payload["trial_active"] = False
            latest_id = connection.execute("SELECT COALESCE(MAX(id), 0) FROM commission_charges").fetchone()[0]
            connection.execute(
                "INSERT INTO cabinet_entitlements(id, payload_json, local_charge_id, balance) VALUES (1, ?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET payload_json = excluded.payload_json, "
                "local_charge_id = excluded.local_charge_id, balance = excluded.balance",
                (json.dumps(payload), latest_id, str(balance)),
            )

    def load_entitlements(self) -> dict | None:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM cabinet_entitlements WHERE id = 1").fetchone()
        return json.loads(row["payload_json"]) if row is not None else None

    def end_trial(self) -> None:
        with self.database.connect() as connection:
            row = connection.execute("SELECT payload_json FROM cabinet_entitlements WHERE id = 1").fetchone()
            if row is not None:
                payload = json.loads(row["payload_json"])
                payload["trial_active"] = False
                connection.execute("UPDATE cabinet_entitlements SET payload_json = ? WHERE id = 1", (json.dumps(payload),))

    def authoritative_balance(self) -> Decimal | None:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM cabinet_entitlements WHERE id = 1").fetchone()
            if row is None:
                return None
            changes = connection.execute(
                "SELECT amount FROM commission_charges WHERE id > ? OR (synced_with_head = 0 AND CAST(amount AS REAL) > 0)", (row["local_charge_id"],),
            ).fetchall()
        return Decimal(row["balance"]) - sum((Decimal(item["amount"]) for item in changes), Decimal("0"))

    def save_settings_cache(
        self,
        broker: str,
        percent: Decimal,
    ) -> None:
        updated_at = (
            datetime
            .now(
                timezone.utc
            )
            .isoformat()
        )

        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO commission_settings_cache (
                    broker,
                    percent,
                    updated_at
                )
                VALUES (?, ?, ?)
                ON CONFLICT(broker)
                DO UPDATE SET
                    percent = excluded.percent,
                    updated_at = excluded.updated_at
                """,
                (
                    broker,
                    str(
                        percent
                    ),
                    updated_at,
                ),
            )

    def load_settings_cache(
        self,
    ) -> dict:
        with self.database.connect() as connection:
            rows = (
                connection
                .execute(
                    """
                    SELECT
                        broker,
                        percent
                    FROM commission_settings_cache
                    """
                )
                .fetchall()
            )

        return {
            str(
                row[
                    "broker"
                ]
            ):
                Decimal(
                    row[
                        "percent"
                    ]
                )

            for row
            in rows
        }
