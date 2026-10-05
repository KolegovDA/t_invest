import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import (
    datetime,
    timezone,
)
from decimal import (
    Decimal,
    InvalidOperation,
)
from typing import Any
from urllib.parse import (
    urlencode,
)

import requests

LIVE_BASE_URL = (
    "https://api.bybit.com"
)

TESTNET_BASE_URL = (
    "https://api-testnet"
    ".bybit.com"
)

DEFAULT_RECV_WINDOW = "5000"

DEFAULT_TIMEOUT_SECONDS = 10.0


class BybitAPIError(
    Exception,
):
    def __init__(
        self,

        ret_code: int,

        ret_msg: str,
    ) -> None:
        self.ret_code = (
            ret_code
        )

        self.ret_msg = (
            ret_msg
        )

        super().__init__(
            "Bybit API error "
            f"{ret_code}: "
            f"{ret_msg}"
        )


def build_signature(
    timestamp: str,

    api_key: str,

    recv_window: str,

    payload: str,

    api_secret: str,
) -> str:
    message = (
        timestamp
        + api_key
        + recv_window
        + payload
    )

    digest = (
        hmac.new(
            api_secret
            .encode("utf-8"),

            message
            .encode("utf-8"),

            hashlib.sha256,
        )
        .hexdigest()
    )

    return digest


def to_decimal(
    value: Any,
) -> Decimal:
    if value is None:
        return Decimal("0")

    text = (
        str(value)
        .strip()
    )

    if not text:
        return Decimal("0")

    try:
        return Decimal(
            text
        )

    except (
        InvalidOperation
    ):
        return Decimal("0")


@dataclass(
    slots=True,
)
class BybitClient:
    api_key: str

    api_secret: str

    base_url: str = (
        LIVE_BASE_URL
    )

    recv_window: str = (
        DEFAULT_RECV_WINDOW
    )

    timeout_seconds: float = (
        DEFAULT_TIMEOUT_SECONDS
    )

    def get_wallet_balance(
        self,

        account_type: str = (
            "UNIFIED"
        ),
    ) -> dict:
        result = (
            self._get(
                path=(
                    "/v5/account/"
                    "wallet-balance"
                ),

                params={
                    "accountType": (
                        account_type
                    ),
                },
            )
        )

        entries = (
            result
            .get("list")
            or []
        )

        if not entries:
            raise (
                BybitAPIError(
                    ret_code=(
                        -1
                    ),

                    ret_msg=(
                        "Bybit account "
                        "list is empty"
                    ),
                )
            )

        entry = (
            entries[0]
        )

        if (
            not isinstance(
                entry,
                dict,
            )
        ):
            raise (
                BybitAPIError(
                    ret_code=(
                        -1
                    ),

                    ret_msg=(
                        "Unexpected Bybit "
                        "account payload"
                    ),
                )
            )

        return entry

    def get_tickers(
        self,

        category: str = "spot",

        symbol: (
            str | None
        ) = None,
    ) -> list[
        dict
    ]:
        params: dict[
            str,
            str
        ] = {
            "category": (
                category
            ),
        }

        if (
            symbol
            is not None
        ):
            params[
                "symbol"
            ] = symbol

        result = (
            self._get(
                path=(
                    "/v5/market/"
                    "tickers"
                ),

                params=(
                    params
                ),
            )
        )

        return list(
            result
            .get("list")
            or []
        )

    def get_instruments_info(
        self,

        category: str = "spot",

        symbol: (
            str | None
        ) = None,
    ) -> list[
        dict
    ]:
        params: dict[
            str,
            str
        ] = {
            "category": (
                category
            ),
        }

        if (
            symbol
            is not None
        ):
            params[
                "symbol"
            ] = symbol

        result = (
            self._get(
                path=(
                    "/v5/market/"
                    "instruments-info"
                ),

                params=(
                    params
                ),
            )
        )

        return list(
            result
            .get("list")
            or []
        )

    def get_fee_rates(self, symbol: str) -> list[dict]:
        result = self._get("/v5/account/fee-rate", {"category": "spot", "symbol": symbol.upper()})
        return list(result.get("list") or [])

    def get_klines(self, symbol: str, interval: str = "W", limit: int = 209, start: int | None = None, end: int | None = None) -> list[list]:
        params = {"category": "spot", "symbol": symbol.upper(), "interval": interval, "limit": str(limit)}
        if start is not None:
            params["start"] = str(start)
        if end is not None:
            params["end"] = str(end)
        result = self._get("/v5/market/kline", params)
        return list(result.get("list") or [])

    def place_spot_order(self, body: dict) -> dict:
        if body.get("category") != "spot" or body.get("isLeverage") != 0:
            raise ValueError("Only non-leveraged spot orders are supported")
        return self._post("/v5/order/create", body)

    def cancel_spot_order(self, symbol: str, order_id: str) -> dict:
        return self._post("/v5/order/cancel", {"category": "spot", "symbol": symbol.upper(), "orderId": order_id})

    def get_spot_orders(self, symbol: str | None = None, order_id: str | None = None, history: bool = False) -> list[dict]:
        params = {"category": "spot", "limit": "50"}
        if symbol:
            params["symbol"] = symbol.upper()
        if order_id:
            params["orderId"] = order_id
        if not history:
            params["openOnly"] = "0" if not order_id else "1"
        return self._paged_list("/v5/order/history" if history else "/v5/order/realtime", params)

    def get_spot_executions(self, order_id: str) -> list[dict]:
        return self._paged_list("/v5/execution/list", {"category": "spot", "orderId": order_id, "limit": "100"})

    def _paged_list(self, path: str, params: dict[str, str]) -> list[dict]:
        rows: list[dict] = []
        seen: set[str] = set()
        params = dict(params)
        while True:
            result = self._get(path, params)
            rows.extend(result.get("list") or [])
            cursor = str(result.get("nextPageCursor") or "")
            if not cursor:
                return rows
            if cursor in seen:
                raise ValueError("Bybit pagination did not advance")
            seen.add(cursor)
            params["cursor"] = cursor

    def get_transaction_log(
        self,

        account_type: str = (
            "UNIFIED"
        ),

        start_time: (
            int | None
        ) = None,

        end_time: (
            int | None
        ) = None,

        limit: int = 50,
    ) -> list[
        dict
    ]:
        entries: (
            list[
                dict
            ]
        ) = []

        cursor = ""
        seen_cursors = set()

        while True:
            params: (
                dict[
                    str,
                    str
                ]
            ) = {
                "accountType": (
                    account_type
                ),

                "limit": (
                    str(
                        limit
                    )
                ),
            }

            if (
                start_time
                is not None
            ):
                params[
                    "startTime"
                ] = str(
                    start_time
                )

            if (
                end_time
                is not None
            ):
                params[
                    "endTime"
                ] = str(
                    end_time
                )

            if cursor:
                params[
                    "cursor"
                ] = cursor

            result = (
                self._get(
                    path=(
                        "/v5/account/"
                        "transaction-log"
                    ),

                    params=(
                        params
                    ),
                )
            )

            page = (
                result
                .get("list")
                or []
            )

            entries.extend(
                entry
                for entry
                in page
                if (
                    isinstance(
                        entry,
                        dict,
                    )
                )
            )

            cursor = (
                str(
                    result
                    .get(
                        "nextPageCursor"
                    )

                    or ""
                )
            )

            if not cursor:
                break
            if cursor in seen_cursors:
                raise ValueError("Bybit transaction pagination did not advance")
            seen_cursors.add(cursor)

        return entries

    def _get(
        self,

        path: str,

        params: dict[
            str,
            str,
        ],
    ) -> dict:
        query_string = (
            urlencode(
                sorted(
                    params
                    .items()
                )
            )
        )

        timestamp = (
            self._timestamp()
        )

        signature = (
            build_signature(
                timestamp=(
                    timestamp
                ),

                api_key=(
                    self
                    .api_key
                ),

                recv_window=(
                    self
                    .recv_window
                ),

                payload=(
                    query_string
                ),

                api_secret=(
                    self
                    .api_secret
                ),
            )
        )

        response = (
            requests.get(
                url=(
                    f"{self.base_url}"
                    f"{path}?"
                    f"{query_string}"
                ),

                headers=(
                    self
                    ._headers(
                        timestamp=(
                            timestamp
                        ),

                        signature=(
                            signature
                        ),
                    )
                ),

                timeout=(
                    self
                    .timeout_seconds
                ),
            )
        )

        return (
            self
            ._parse_response(
                response
            )
        )

    def _post(
        self,

        path: str,

        body: dict,
    ) -> dict:
        payload = (
            json.dumps(
                body,

                separators=(
                    ",",
                    ":",
                ),
            )
        )

        timestamp = (
            self._timestamp()
        )

        signature = (
            build_signature(
                timestamp=(
                    timestamp
                ),

                api_key=(
                    self
                    .api_key
                ),

                recv_window=(
                    self
                    .recv_window
                ),

                payload=(
                    payload
                ),

                api_secret=(
                    self
                    .api_secret
                ),
            )
        )

        response = (
            requests.post(
                url=(
                    f"{self.base_url}"
                    f"{path}"
                ),

                headers=(
                    self
                    ._headers(
                        timestamp=(
                            timestamp
                        ),

                        signature=(
                            signature
                        ),
                    )
                ),

                data=(
                    payload
                    .encode(
                        "utf-8"
                    )
                ),

                timeout=(
                    self
                    .timeout_seconds
                ),
            )
        )

        return (
            self
            ._parse_response(
                response
            )
        )

    def _headers(
        self,

        timestamp: str,

        signature: str,
    ) -> dict[
        str,
        str
    ]:
        return {
            "X-BAPI-API-Key": (
                self
                .api_key
            ),

            "X-BAPI-Timestamp": (
                timestamp
            ),

            "X-BAPI-Recv-Window": (
                self
                .recv_window
            ),

            "X-BAPI-SIGN": (
                signature
            ),

            "Content-Type": (
                "application/"
                "json"
            ),
        }

    @staticmethod
    def _timestamp(
    ) -> str:
        now = (
            datetime
            .now(
                timezone
                .utc
            )
        )

        return str(
            int(
                now
                .timestamp()
                * 1000
            )
        )

    @staticmethod
    def _parse_response(
        response: (
            requests
            .Response
        ),
    ) -> dict:
        (
            response
            .raise_for_status()
        )

        data = (
            response
            .json()
        )

        ret_code = int(
            data
            .get("retCode")
            or 0
        )

        if (
            ret_code
            != 0
        ):
            raise (
                BybitAPIError(
                    ret_code=(
                        ret_code
                    ),

                    ret_msg=(
                        str(
                            data
                            .get(
                                "retMsg"
                            )

                            or ""
                        )
                    ),
                )
            )

        result = (
            data
            .get("result")
        )

        if (
            not isinstance(
                result,
                dict,
            )
        ):
            return {}

        return result
