from __future__ import annotations

import socket
import threading
from dataclasses import (
    dataclass,
)
from decimal import (
    Decimal,
)
from typing import Any

import requests


SYNC_INTERVAL_SECONDS = (
    5 * 60
)


@dataclass(slots=True)
class HeadServerClient:
    """
    7.3 плана v1.2: связь
    с головным сервером.

    Регистрация пользователя,
    авторизация и периодическая
    репликация данных
    (счета, платформы,
    инструменты, балансы,
    прибыль).

    Все вызовы best-effort:
    недоступность головного
    сервера не влияет на
    работу клиента.
    """

    base_url: str

    timeout_seconds: int = 15

    def register_user(
        self,
        stored_user,
    ) -> str | None:
        return (
            self
            ._post_json(
                "/head/api/clients/register",

                {
                    "full_name": (
                        stored_user
                        .full_name
                    ),

                    "phone": (
                        stored_user
                        .phone
                    ),

                    "email": (
                        stored_user
                        .email
                    ),

                    "birth_date": (
                        stored_user
                        .birth_date
                    ),

                    "login": (
                        stored_user
                        .login
                    ),

                    "password_hash": (
                        stored_user
                        .password_hash
                    ),

                    "machine_label": (
                        self
                        .machine_label()
                    ),
                },
            )
            or None
        )

    def login_user(
        self,
        login: str,
        password_hash: str,
    ) -> str | None:
        result = (
            self
            ._post_json(
                "/head/api/clients/login",

                {
                    "login": (
                        login
                    ),

                    "password_hash": (
                        password_hash
                    ),
                },
            )
        )

        if (
            result
            is None
        ):
            return None

        api_key = (
            result
            .get(
                "api_key"
            )
        )

        return (
            str(
                api_key
            )

            if api_key

            else None
        )

    def push_sync(
        self,
        api_key: str,
        payload: dict,
    ) -> bool:
        result = (
            self
            ._post_json(
                "/head/api/sync",

                {
                    "payload": (
                        payload
                    ),
                },

                api_key=(
                    api_key
                ),
            )
        )

        return (
            result
            is not None
        )

    def _post_json(
        self,
        path: str,
        body: dict,

        api_key: (
            str | None
        ) = None,
    ) -> (
        dict | None
    ):
        headers = {
            "Content-Type": (
                "application/json"
            ),
        }

        if (
            api_key
            is not None
        ):
            headers[
                "X-Api-Key"
            ] = (
                api_key
            )

        url = (
            self
            .base_url
            .rstrip(
                "/"
            )

            + path
        )

        try:
            response = (
                requests
                .post(
                    url,

                    json=(
                        body
                    ),

                    headers=(
                        headers
                    ),

                    timeout=(
                        self
                        .timeout_seconds
                    ),
                )
            )

            if (
                response
                .status_code
                >= 400
            ):
                print(
                    "HEAD SERVER CLIENT:",
                    url,

                    "HTTP",

                    (
                        response
                        .status_code
                    ),
                )

                return None

            return (
                response
                .json()
            )

        except Exception as error:
            print(
                "HEAD SERVER CLIENT ERROR:",
                url,

                repr(
                    error
                ),
            )

            return None

    @staticmethod
    def machine_label() -> str:
        try:
            return (
                socket
                .gethostname()
            )

        except Exception:
            return (
                "unknown"
            )


@dataclass(slots=True)
class HeadSyncPayloadBuilder:
    """
    Собирает реплицируемый
    payload: счета, платформы,
    инструменты, начальный и
    текущий баланс, прибыль,
    последние операции.
    """

    trading_account_service: Any

    trading_state_repository: Any

    account_performance_service: Any

    operation_log_repository: Any

    def build(
        self,
    ) -> dict:
        accounts = []

        platforms = (
            set()
        )

        instruments = (
            set()
        )

        initial_balance = (
            Decimal("0")
        )

        current_balance = (
            Decimal("0")
        )

        total_profit = (
            Decimal("0")
        )

        deposits_total = (
            Decimal("0")
        )

        try:
            account_list = (
                self
                .trading_account_service
                .get_all()
            )

        except Exception:
            account_list = []

        for account in account_list:
            platforms.add(
                account
                .broker
                .value
            )

            performance = (
                self
                .account_performance_service
                .build_report(
                    trading_account_id=(
                        account
                        .id
                    ),

                    broker_account_id=(
                        account
                        .broker_account_id
                    ),
                )
            )

            deposits_total += (
                performance
                .deposits_total
            )

            current_balance += (
                performance
                .historical_balance
            )

            total_profit += (
                performance
                .realized_profit

                + (
                    performance
                    .unrealized_profit
                )
            )

            accounts.append(
                {
                    "id": (
                        account
                        .id
                    ),

                    "name": (
                        account
                        .name
                    ),

                    "broker": (
                        account
                        .broker
                        .value
                    ),

                    "broker_account_id": (
                        account
                        .broker_account_id
                    ),

                    "mode": (
                        account
                        .mode
                        .value
                    ),

                    "enabled": (
                        account
                        .enabled
                    ),

                    "net_deposits": (
                        str(
                            performance
                            .net_deposits
                        )
                    ),

                    "historical_balance": (
                        str(
                            performance
                            .historical_balance
                        )
                    ),

                    "realized_profit": (
                        str(
                            performance
                            .realized_profit
                        )
                    ),

                    "unrealized_profit": (
                        str(
                            performance
                            .unrealized_profit
                        )
                    ),

                    "roe_percent": (
                        str(
                            performance
                            .roe_percent
                        )

                        if (
                            performance
                            .roe_percent
                            is not None
                        )

                        else None
                    ),

                    "roi_percent": (
                        str(
                            performance
                            .roi_percent
                        )

                        if (
                            performance
                            .roi_percent
                            is not None
                        )

                        else None
                    ),
                }
            )

        try:
            snapshots = (
                self
                .trading_state_repository
                .get_all()
            )

        except Exception:
            snapshots = []

        for snapshot in snapshots:
            initial_deposit = (
                getattr(
                    snapshot,

                    "initial_deposit",

                    None,
                )
            )

            if (
                initial_deposit
                is not None
            ):
                initial_balance += (
                    Decimal(
                        str(
                            initial_deposit
                        )
                    )
                )

            for (
                instrument
            ) in (
                snapshot
                .instruments
            ):
                instruments.add(
                    instrument
                    .ticker
                )

        operations = []

        try:
            events = (
                self
                .operation_log_repository
                .recent(
                    limit=50,
                )
            )

            operations = [
                {
                    "created_at": (
                        event
                        .created_at
                    ),

                    "event_type": (
                        event
                        .event_type
                    ),

                    "ticker": (
                        event
                        .ticker
                    ),

                    "details": (
                        event
                        .details
                    ),
                }

                for event
                in events
            ]

        except Exception:
            operations = []

        roe_percent = (
            (
                total_profit
                / deposits_total
                * Decimal(
                    "100"
                )
            )

            if (
                deposits_total
                != 0
            )

            else None
        )

        return {
            "accounts": (
                accounts
            ),

            "platforms": (
                sorted(
                    platforms
                )
            ),

            "instruments": (
                sorted(
                    instruments
                )
            ),

            "initial_balance": (
                str(
                    initial_balance
                )
            ),

            "current_balance": (
                str(
                    current_balance
                )
            ),

            "total_profit": (
                str(
                    total_profit
                )
            ),

            "roe_percent": (
                str(
                    roe_percent
                )

                if (
                    roe_percent
                    is not None
                )

                else None
            ),

            "operations": (
                operations
            ),
        }


@dataclass(slots=True)
class HeadReplicationWorker:
    """
    Фоновая репликация:
    раз в 5 минут отправляет
    payload на головной
    сервер.
    """

    client: (
        HeadServerClient
        | None
    )

    payload_builder: (
        HeadSyncPayloadBuilder
        | None
    )

    user_repository: Any

    interval_seconds: int = (
        SYNC_INTERVAL_SECONDS
    )

    def start(
        self,
    ) -> None:
        thread = (
            threading
            .Thread(
                target=(
                    self
                    ._run
                ),

                daemon=(
                    True
                ),
            )
        )

        thread.start()

    def sync_now(
        self,
    ) -> bool:
        if (
            self.client
            is None

            or (
                self
                .payload_builder
                is None
            )
        ):
            return False

        api_key = (
            self
            ._current_api_key()
        )

        if (
            not api_key
        ):
            return False

        payload = (
            self
            .payload_builder
            .build()
        )

        return (
            self
            .client
            .push_sync(
                api_key=(
                    api_key
                ),

                payload=(
                    payload
                ),
            )
        )

    def _current_api_key(
        self,
    ) -> (
        str | None
    ):
        try:
            users = (
                self
                .user_repository
                .count_users()
            )

            if (
                users
                == 0
            ):
                return None

            with_id = (
                self
                .user_repository
                .get_user_by_id(
                    1
                )
            )

            if (
                with_id
                is None
            ):
                return None

            return (
                with_id
                .head_api_key
            )

        except Exception:
            return None

    def _run(
        self,
    ) -> None:
        import time

        while True:
            time.sleep(
                self
                .interval_seconds
            )

            try:
                self.sync_now()

            except Exception as error:
                print(
                    "HEAD REPLICATION ERROR:",
                    repr(
                        error
                    ),
                )
