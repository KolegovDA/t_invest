from __future__ import annotations

import sqlite3

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from domain.trading_account import (
    BrokerType,
    CommissionMode,
    TradingAccount,
    TradingAccountMode,
)


@dataclass(slots=True)
class StoredTradingAccount:
    account: TradingAccount

    protected_credentials: str


@dataclass(slots=True)
class TradingAccountRepository:
    db_path: str

    def __post_init__(
        self,
    ) -> None:
        self._ensure_database()

    def _connect(
        self,
    ) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.db_path
        )

        connection.row_factory = (
            sqlite3.Row
        )

        return connection

    def _ensure_database(
        self,
    ) -> None:
        path = Path(
            self.db_path
        )

        if (
            path.parent
            != Path(".")
        ):
            path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS
                trading_accounts (
                    id TEXT PRIMARY KEY,

                    name TEXT NOT NULL,

                    broker TEXT NOT NULL
                        DEFAULT 'tinvest',

                    broker_account_id
                        TEXT NOT NULL,

                    mode TEXT NOT NULL,

                    protected_credentials
                        TEXT NOT NULL,

                    commission_mode
                        TEXT NOT NULL,

                    custom_buy_commission_percent
                        TEXT,

                    custom_sell_commission_percent
                        TEXT,

                    detected_buy_commission_percent
                        TEXT,

                    detected_sell_commission_percent
                        TEXT,

                    enabled INTEGER NOT NULL
                        DEFAULT 1,

                    created_at TEXT NOT NULL,

                    updated_at TEXT NOT NULL
                )
                """
            )

            #
            # Миграция ранней версии 1.1.
            #
            columns = {
                row["name"]
                for row
                in connection.execute(
                    """
                    PRAGMA table_info(
                        trading_accounts
                    )
                    """
                ).fetchall()
            }

            if (
                "broker"
                not in columns
            ):
                connection.execute(
                    """
                    ALTER TABLE
                        trading_accounts
                    ADD COLUMN
                        broker TEXT
                        NOT NULL
                        DEFAULT 'tinvest'
                    """
                )

            if (
                "protected_credentials"
                not in columns
                and "protected_token"
                in columns
            ):
                connection.execute(
                    """
                    ALTER TABLE
                        trading_accounts
                    ADD COLUMN
                        protected_credentials
                        TEXT
                    """
                )

                connection.execute(
                    """
                    UPDATE trading_accounts
                    SET protected_credentials =
                        protected_token
                    WHERE
                        protected_credentials
                        IS NULL
                    """
                )

            #
            # Старый индекс нельзя
            # использовать для
            # multi-broker.
            #
            connection.execute(
                """
                DROP INDEX IF EXISTS
                idx_trading_accounts_broker_mode
                """
            )

            connection.execute(
                """
                CREATE UNIQUE INDEX
                IF NOT EXISTS
                idx_trading_accounts_unique
                ON trading_accounts (
                    broker,
                    broker_account_id,
                    mode
                )
                """
            )

            connection.execute(
                """
                CREATE INDEX
                IF NOT EXISTS
                idx_trading_accounts_enabled
                ON trading_accounts (
                    enabled
                )
                """
            )

            connection.commit()

    def save(
        self,

        account: TradingAccount,

        protected_credentials: str,
    ) -> None:
        if (
            account.created_at
            is None
        ):
            raise ValueError(
                "created_at is required"
            )

        if (
            account.updated_at
            is None
        ):
            raise ValueError(
                "updated_at is required"
            )

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO
                trading_accounts (
                    id,
                    name,
                    broker,
                    broker_account_id,
                    mode,
                    protected_credentials,
                    commission_mode,
                    custom_buy_commission_percent,
                    custom_sell_commission_percent,
                    detected_buy_commission_percent,
                    detected_sell_commission_percent,
                    enabled,
                    created_at,
                    updated_at
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?
                )

                ON CONFLICT(id)
                DO UPDATE SET
                    name =
                        excluded.name,

                    broker =
                        excluded.broker,

                    broker_account_id =
                        excluded.broker_account_id,

                    mode =
                        excluded.mode,

                    protected_credentials =
                        excluded.protected_credentials,

                    commission_mode =
                        excluded.commission_mode,

                    custom_buy_commission_percent =
                        excluded.custom_buy_commission_percent,

                    custom_sell_commission_percent =
                        excluded.custom_sell_commission_percent,

                    detected_buy_commission_percent =
                        excluded.detected_buy_commission_percent,

                    detected_sell_commission_percent =
                        excluded.detected_sell_commission_percent,

                    enabled =
                        excluded.enabled,

                    updated_at =
                        excluded.updated_at
                """,

                (
                    account.id,

                    account.name,

                    account.broker.value,

                    account
                    .broker_account_id,

                    account.mode.value,

                    protected_credentials,

                    account
                    .commission_mode
                    .value,

                    self._decimal_to_text(
                        account
                        .custom_buy_commission_percent
                    ),

                    self._decimal_to_text(
                        account
                        .custom_sell_commission_percent
                    ),

                    self._decimal_to_text(
                        account
                        .detected_buy_commission_percent
                    ),

                    self._decimal_to_text(
                        account
                        .detected_sell_commission_percent
                    ),

                    1
                    if account.enabled
                    else 0,

                    account
                    .created_at
                    .isoformat(),

                    account
                    .updated_at
                    .isoformat(),
                ),
            )

            connection.commit()

    def get(
        self,
        account_id: str,
    ) -> StoredTradingAccount | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM trading_accounts
                WHERE id = ?
                """,

                (
                    account_id,
                ),
            ).fetchone()

        if row is None:
            return None

        return self._from_row(
            row
        )

    def get_all(
        self,
    ) -> list[
        StoredTradingAccount
    ]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM trading_accounts
                ORDER BY
                    enabled DESC,
                    created_at ASC
                """
            ).fetchall()

        return [
            self._from_row(
                row
            )
            for row
            in rows
        ]

    def get_enabled(
        self,
    ) -> list[
        StoredTradingAccount
    ]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM trading_accounts
                WHERE enabled = 1
                ORDER BY created_at ASC
                """
            ).fetchall()

        return [
            self._from_row(
                row
            )
            for row
            in rows
        ]

    def delete(
        self,
        account_id: str,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                DELETE FROM
                    trading_accounts
                WHERE id = ?
                """,

                (
                    account_id,
                ),
            )

            connection.commit()

    def broker_account_exists(
        self,

        broker: BrokerType,

        broker_account_id: str,

        mode: TradingAccountMode,

        exclude_id: (
            str | None
        ) = None,
    ) -> bool:
        query = """
            SELECT id
            FROM trading_accounts
            WHERE
                broker = ?
                AND broker_account_id = ?
                AND mode = ?
        """

        parameters: list[
            object
        ] = [
            broker.value,
            broker_account_id,
            mode.value,
        ]

        if (
            exclude_id
            is not None
        ):
            query += (
                " AND id != ?"
            )

            parameters.append(
                exclude_id
            )

        with self._connect() as connection:
            row = connection.execute(
                query,

                tuple(
                    parameters
                ),
            ).fetchone()

        return (
            row is not None
        )

    def _from_row(
        self,
        row: sqlite3.Row,
    ) -> StoredTradingAccount:
        broker_value = (
            row["broker"]
            if "broker" in row.keys()
            else "tinvest"
        )

        protected_credentials = (
            row[
                "protected_credentials"
            ]
        )

        account = TradingAccount(
            id=row["id"],

            name=row["name"],

            broker=BrokerType(
                broker_value
            ),

            broker_account_id=(
                row[
                    "broker_account_id"
                ]
            ),

            mode=TradingAccountMode(
                row["mode"]
            ),

            commission_mode=(
                CommissionMode(
                    row[
                        "commission_mode"
                    ]
                )
            ),

            custom_buy_commission_percent=(
                self._text_to_decimal(
                    row[
                        "custom_buy_commission_percent"
                    ]
                )
            ),

            custom_sell_commission_percent=(
                self._text_to_decimal(
                    row[
                        "custom_sell_commission_percent"
                    ]
                )
            ),

            detected_buy_commission_percent=(
                self._text_to_decimal(
                    row[
                        "detected_buy_commission_percent"
                    ]
                )
            ),

            detected_sell_commission_percent=(
                self._text_to_decimal(
                    row[
                        "detected_sell_commission_percent"
                    ]
                )
            ),

            enabled=bool(
                row["enabled"]
            ),

            created_at=(
                datetime.fromisoformat(
                    row["created_at"]
                )
            ),

            updated_at=(
                datetime.fromisoformat(
                    row["updated_at"]
                )
            ),
        )

        return StoredTradingAccount(
            account=account,

            protected_credentials=(
                protected_credentials
            ),
        )

    @staticmethod
    def _decimal_to_text(
        value: Decimal | None,
    ) -> str | None:
        if value is None:
            return None

        return str(value)

    @staticmethod
    def _text_to_decimal(
        value: str | None,
    ) -> Decimal | None:
        if value is None:
            return None

        return Decimal(
            value
        )
