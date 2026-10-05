from __future__ import annotations

import hashlib
import os
import socket
import threading
import time
from dataclasses import (
    dataclass,
    field,
)
from decimal import (
    Decimal,
)
from typing import Any

import requests


SYNC_INTERVAL_SECONDS = (
    120
)


HEARTBEAT_INTERVAL_SECONDS = (
    60
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
    _browser_devices_retry_at: float = field(default=0, init=False)
    _warned_browser_devices_unsupported: bool = field(default=False, init=False)

    def register_user(
        self,
        stored_user,
    ) -> dict | None:
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

    def confirm_password_reset(
        self,
        login: str,
        code: str,
        new_password_hash: str,
    ) -> tuple[
        str | None,
        str | None,
    ]:
        """
        Подтверждение сброса
        пароля кодом от
        администратора.

        Возвращает
        (api_key, None)
        при успехе либо
        (None, сообщение
        об ошибке).
        """

        url = (
            self
            .base_url
            .rstrip(
                "/"
            )

            + "/head/api/clients/"
            "password-reset/confirm"
        )

        try:
            response = (
                requests
                .post(
                    url,

                    json={
                        "login": (
                            login
                        ),

                        "code": (
                            code
                        ),

                        "new_password_hash": (
                            new_password_hash
                        ),
                    },

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
                detail = (
                    "Головной сервер "
                    "вернул ошибку"
                )

                try:
                    payload = (
                        response
                        .json()
                    )

                    if (
                        payload
                        and payload
                        .get(
                            "detail"
                        )
                    ):
                        detail = (
                            str(
                                payload[
                                    "detail"
                                ]
                            )
                        )

                except Exception:
                    pass

                return (
                    None,
                    detail,
                )

            api_key = (
                response
                .json()
                .get(
                    "api_key"
                )
            )

            if not api_key:
                return (
                    None,

                    "Головной сервер "
                    "не вернул api_key",
                )

            return (
                str(
                    api_key
                ),

                None,
            )

        except Exception as error:
            print(
                "HEAD SERVER CLIENT ERROR:",
                url,

                repr(
                    error
                ),
            )

            return (
                None,

                "Головной сервер "
                "недоступен",
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

                    "device_key": (
                        self
                        .device_key()
                    ),

                    "machine_label": (
                        self
                        .machine_label()
                    ),
                    "software_endpoint": self.software_endpoint(),
                },

                api_key=(
                    api_key
                ),
            )
        )

        return isinstance(result, dict) and result.get("status") == "ok"

    def push_browser_devices(self, api_key: str, devices: list[dict]) -> bool:
        if time.monotonic() < self._browser_devices_retry_at:
            return False
        result = self._post_json("/head/api/clients/browser-devices", {
            "installation_key": self.device_key(), "devices": devices,
        }, api_key=api_key)
        return isinstance(result, dict) and result.get("status") == "ok"

    def send_heartbeat(
        self,
        api_key: str,
    ) -> bool:
        result = (
            self
            ._post_json(
                "/head/api/clients"
                "/heartbeat",

                {
                    "device_key": (
                        self
                        .device_key()
                    ),

                    "machine_label": (
                        self
                        .machine_label()
                    ),
                    "software_endpoint": self.software_endpoint(),
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

    def fetch_history(
        self,
        api_key: str,
        limit: int = 20,
    ) -> (
        dict | None
    ):
        headers = {
            "X-Api-Key": (
                api_key
            ),
        }

        url = (
            self
            .base_url
            .rstrip(
                "/"
            )

            + (
                "/head/api/clients"
                "/history?limit="
                + str(
                    limit
                )
            )
        )

        try:
            response = (
                requests
                .get(
                    url,

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

    def fetch_config(
        self,
        api_key: str,
    ) -> (
        dict | None
    ):
        headers = {
            "X-Api-Key": (
                api_key
            ),
        }

        url = (
            self
            .base_url
            .rstrip(
                "/"
            )

            + "/head/api/config"
        )

        try:
            response = (
                requests
                .get(
                    url,

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

    def submit_topup(
        self,
        api_key: str,
        amount: str,
        comment: str = "",
        document_name: (
            str | None
        ) = None,
        document_mime: (
            str | None
        ) = None,
        document_base64: (
            str | None
        ) = None,
    ) -> tuple[
        dict | None,
        str | None,
    ]:
        """
        B4: заявка на пополнение
        баланса ЛК (с необязательным
        документом/фото в base64).

        Возвращает
        (заявка, None) при успехе
        либо (None, сообщение
        об ошибке).
        """

        url = (
            self
            .base_url
            .rstrip(
                "/"
            )

            + "/head/api/clients"
            "/topups"
        )

        body = {
            "amount": (
                amount
            ),

            "comment": (
                comment
            ),

            "document_name": (
                document_name
            ),

            "document_mime": (
                document_mime
            ),

            "document_base64": (
                document_base64
            ),
        }

        try:
            response = (
                requests
                .post(
                    url,

                    json=(
                        body
                    ),

                    headers={
                        "X-Api-Key": (
                            api_key
                        ),
                    },

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
                detail = (
                    "Головной сервер "
                    "вернул ошибку"
                )

                try:
                    payload = (
                        response
                        .json()
                    )

                    if (
                        payload
                        and payload
                        .get(
                            "detail"
                        )
                    ):
                        detail = (
                            str(
                                payload[
                                    "detail"
                                ]
                            )
                        )

                except Exception:
                    pass

                return (
                    None,
                    detail,
                )

            result = (
                response
                .json()
                .get(
                    "request"
                )
            )

            if not isinstance(
                result,
                dict,
            ):
                return (
                    None,

                    "Головной сервер "
                    "не вернул заявку",
                )

            return (
                result,
                None,
            )

        except Exception as error:
            print(
                "HEAD SERVER CLIENT ERROR:",
                url,

                repr(
                    error
                ),
            )

            return (
                None,

                "Головной сервер "
                "недоступен",
            )

    def fetch_topups(
        self,
        api_key: str,
    ) -> (
        dict | None
    ):
        """
        B4: список заявок клиента
        на пополнение и баланс ЛК
        на головном сервере.
        """

        headers = {
            "X-Api-Key": (
                api_key
            ),
        }

        url = (
            self
            .base_url
            .rstrip(
                "/"
            )

            + "/head/api/clients"
            "/topups"
        )

        try:
            response = (
                requests
                .get(
                    url,

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

            if path == "/head/api/clients/browser-devices" and response.status_code in (404, 405):
                self._browser_devices_retry_at = time.monotonic() + 300
                if not self._warned_browser_devices_unsupported:
                    print("HEAD SERVER CLIENT: голова не поддерживает browser-devices; требуется обновление головы. Торговля и основная синхронизация продолжаются.")
                    self._warned_browser_devices_unsupported = True
                return None
            if path == "/head/api/clients/browser-devices" and response.status_code < 400:
                self._browser_devices_retry_at = 0
                self._warned_browser_devices_unsupported = False

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
    def software_endpoint() -> str | None:
        host = os.getenv("ESM_WEB_BIND_HOST")
        port = os.getenv("ESM_WEB_BOUND_PORT")
        if not host or not port or not port.isdigit() or not 1 <= int(port) <= 65535:
            return None
        address = socket.gethostname() if host in {"0.0.0.0", "::"} else host
        if ":" in address:
            address = f"[{address}]"
        return f"http://{address}:{port}"

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

    @staticmethod
    def device_key() -> str:
        try:
            hostname = (
                socket
                .gethostname()
            )

        except Exception:
            hostname = (
                "unknown"
            )

        return (
            hashlib
            .sha256(
                (
                    "esm-device:"
                    + hostname
                )
                .encode(
                    "utf-8"
                )
            )
            .hexdigest()[
                :32
            ]
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
    balance_snapshot_repository: Any = None
    broker_registry: Any = None

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

        for account in accounts:
            account["initial_balance"] = str(sum((
                Decimal(str(snapshot.initial_deposit or "0"))
                for snapshot in snapshots if snapshot.trading_account_id == account["id"]
            ), Decimal("0")))
            if self.broker_registry is not None and account["enabled"] and account["mode"] == "live":
                try:
                    configured = next(item for item in account_list if item.id == account["id"])
                    portfolio = self.broker_registry.get(configured.broker).get_portfolio(
                        credentials=self.trading_account_service.get_credentials(configured.id),
                        broker_account_id=configured.broker_account_id, mode=configured.mode,
                    )
                    account["current_balance"] = str(portfolio.total_value if portfolio.total_value is not None else portfolio.cash)
                except Exception:
                    pass
            account["instruments"] = sorted({
                instrument.ticker
                for snapshot in snapshots
                if snapshot.trading_account_id == account["id"]
                for instrument in snapshot.instruments
            })

        balance_history = []
        if self.balance_snapshot_repository is not None:
            from datetime import datetime, timedelta, timezone
            balance_history = [
                {"created_at": item.created_at, "trading_account_id": item.trading_account_id,
                 "currency": item.currency, "equity": str(item.equity)}
                for item in self.balance_snapshot_repository.get_since(
                    (datetime.now(timezone.utc) - timedelta(days=180)).isoformat(),
                )
            ]

        return {
            "balance_history": balance_history,
            "sessions": [snapshot.to_dict() for snapshot in snapshots if hasattr(snapshot, "to_dict")],
            "closed_grids": self.trading_state_repository.closed_grids() if hasattr(self.trading_state_repository, "closed_grids") else [],
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

    v1.3: вместе с payload
    уходят несинхронизированные
    комиссии, а в ответ
    подтягивается конфиг
    комиссии (проценты по
    платформам пользователя).
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

    commission_repository: (
        Any | None
    ) = None

    commission_service: (
        Any | None
    ) = None

    trading_settings_service: (
        Any | None
    ) = None

    operation_log_repository: (
        Any | None
    ) = None

    topup_service: (
        Any | None
    ) = None

    interval_seconds: int = (
        SYNC_INTERVAL_SECONDS
    )

    _warned_missing_api_key: (
        bool
    ) = False

    _logged_heartbeat_ok: (
        bool
    ) = False

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

        pending_charges = (
            self
            ._pending_commission_charges()
        )

        if pending_charges:
            payload[
                "commission_charges"
            ] = [
                charge
                .to_dict()

                for charge
                in pending_charges
            ]

        pending_control_logs = (
            self
            ._pending_control_logs()
        )

        if pending_control_logs:
            payload[
                "control_logs"
            ] = [
                entry
                .to_dict()

                for entry
                in pending_control_logs
            ]

        pushed = (
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

        if pushed:
            self\
                ._mark_commission_synced(
                    pending_charges
                )

            self\
                ._mark_control_logs_synced(
                    pending_control_logs
                )

        self\
            ._refresh_head_config(
                api_key=(
                    api_key
                ),
            )

        self\
            ._refresh_topups()

        return pushed

    def _refresh_topups(
        self,
    ) -> None:
        """
        B4: подтягивает статусы
        заявок на пополнение и
        зачисляет подтверждённые
        пополнения в локальный
        баланс.
        """

        if (
            self
            .topup_service
            is None
        ):
            return

        try:
            (
                self
                .topup_service
                .refresh_topups()
            )

        except Exception as error:
            print(
                "TOPUP REFRESH ERROR:",
                repr(
                    error
                ),
            )

    def _pending_commission_charges(
        self,
    ) -> list:
        if (
            self
            .commission_repository
            is None
        ):
            return []

        try:
            return (
                self
                .commission_repository
                .pending_unsynced()
            )

        except Exception as error:
            print(
                "COMMISSION SYNC READ ERROR:",
                repr(
                    error
                ),
            )

            return []

    def _mark_commission_synced(
        self,
        charges: list,
    ) -> None:
        if (
            self
            .commission_repository
            is None
        ):
            return

        if not charges:
            return

        try:
            self\
                .commission_repository\
                .mark_synced(
                    [
                        charge
                        .id

                        for charge
                        in charges
                    ]
                )

        except Exception as error:
            print(
                "COMMISSION SYNC MARK ERROR:",
                repr(
                    error
                ),
            )

    def _pending_control_logs(
        self,
    ) -> list:
        if (
            self
            .operation_log_repository
            is None
        ):
            return []

        try:
            return (
                self
                .operation_log_repository
                .pending_control_logs()
            )

        except Exception as error:
            print(
                "CONTROL LOG SYNC READ ERROR:",
                repr(
                    error
                ),
            )

            return []

    def _mark_control_logs_synced(
        self,
        entries: list,
    ) -> None:
        if (
            self
            .operation_log_repository
            is None
        ):
            return

        if not entries:
            return

        try:
            self\
                .operation_log_repository\
                .mark_control_logs_synced(
                    [
                        entry
                        .id

                        for entry
                        in entries
                    ]
                )

        except Exception as error:
            print(
                "CONTROL LOG SYNC MARK ERROR:",
                repr(
                    error
                ),
            )

    def _refresh_head_config(
        self,
        api_key: str,
    ) -> None:
        if self.client is None:
            return
        if self.commission_service is None and self.trading_settings_service is None:
            return
        try:
            config = self.client.fetch_config(api_key=api_key)
        except Exception as error:
            print("HEAD CONFIG REFRESH ERROR:", repr(error))
            return
        if config is None:
            return
        for service in (self.commission_service, self.trading_settings_service):
            if service is None:
                continue
            try:
                service.apply_head_config(config)
            except Exception as error:
                print("HEAD CONFIG APPLY ERROR:", repr(error))

    def retry_pending_head_users(
        self,
    ) -> None:
        """
        Доставка отложенных
        регистраций: если головной
        сервер был недоступен при
        регистрации, данные
        отправляются здесь при
        появлении связи.
        """

        if (
            self.client
            is None
        ):
            return

        try:
            pending = (
                self
                .user_repository
                .list_users_without_head_api_key()
            )

        except Exception as error:
            print(
                "HEAD PENDING USERS ERROR:",
                repr(
                    error
                ),
            )

            return

        for stored in pending:
            try:
                api_key = (
                    None
                )

                result = (
                    self
                    .client
                    .register_user(
                        stored_user=(
                            stored
                        ),
                    )
                )

                if (
                    result
                    is not None
                ):
                    value = (
                        result
                        .get(
                            "api_key"
                        )
                    )

                    api_key = (
                        str(
                            value
                        )

                        if value

                        else None
                    )

                if (
                    api_key
                    is None
                ):
                    api_key = (
                        self
                        .client
                        .login_user(
                            login=(
                                stored
                                .login
                            ),

                            password_hash=(
                                stored
                                .password_hash
                            ),
                        )
                    )

                if api_key:
                    self\
                        .user_repository\
                        .set_user_head_api_key(
                            user_id=(
                                stored
                                .id
                            ),

                            api_key=(
                                api_key
                            ),
                        )

                    (
                        self
                        .sync_now()
                    )

            except Exception as error:
                print(
                    "HEAD PENDING REGISTER ERROR:",
                    repr(
                        error
                    ),
                )

    def _current_api_key(
        self,
    ) -> (
        str | None
    ):
        try:
            user = self.user_repository.get_first_user_with_head_api_key()
            return user.head_api_key if user is not None else None

        except Exception:
            return None

    def _send_heartbeat(
        self,
    ) -> None:
        if (
            self.client
            is None
        ):
            return

        api_key = (
            self
            ._current_api_key()
        )

        if (
            not api_key
        ):
            if (
                not (
                    self
                    ._warned_missing_api_key
                )
            ):
                self\
                    ._warned_missing_api_key = (
                        True
                    )

                print(
                    "HEAD HEARTBEAT: "
                    "нет api_key — "
                    "клиент не "
                    "зарегистрирован "
                    "на головном "
                    "сервере",
                )

            return

        try:
            delivered = (
                self
                .client
                .send_heartbeat(
                    api_key=(
                        api_key
                    ),
                )
            )

            if hasattr(self.user_repository, "browser_devices_for_head"):
                devices = self.user_repository.browser_devices_for_head(api_key)
                self.client.push_browser_devices(api_key, devices)

            if (
                delivered

                and not (
                    self
                    ._logged_heartbeat_ok
                )
            ):
                self\
                    ._logged_heartbeat_ok = (
                        True
                    )

                print(
                    "HEAD HEARTBEAT: "
                    "головной сервер "
                    "отвечает",
                )

        except Exception as error:
            print(
                "HEAD HEARTBEAT ERROR:",
                repr(
                    error
                ),
            )

    def _run(
        self,
    ) -> None:
        import time

        ticks = (
            max(
                1,

                (
                    self
                    .interval_seconds
                )
                // (
                    HEARTBEAT_INTERVAL_SECONDS
                ),
            )
        )

        while True:
            self.retry_pending_head_users()
            try:
                self.sync_now()
            except Exception as error:
                print("HEAD REPLICATION ERROR:", repr(error))

            for _ in range(
                ticks,
            ):
                (
                    self
                    ._send_heartbeat()
                )

                time.sleep(
                    HEARTBEAT_INTERVAL_SECONDS
                )
