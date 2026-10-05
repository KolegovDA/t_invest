from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from decimal import Decimal
from typing import Any


allowed_days = (
    7,
    30,
    90,
    180,
)


#
# Формат v1.2: "прибыль=",
# v1.5: "факт=" (рядом
# с "расчётная=").
#
profit_pattern = re.compile(
    r"(?:факт|прибыль)=(-?\d+(?:\.\d+)?)"
)


def _parse_timestamp(
    value: str,
) -> (
    datetime | None
):
    try:
        parsed = (
            datetime
            .fromisoformat(
                value,
            )
        )

    except (
        TypeError,
        ValueError,
    ):
        return None

    if (
        parsed.tzinfo
        is None
    ):
        return (
            parsed
            .replace(
                tzinfo=(
                    timezone.utc
                ),
            )
        )

    return (
        parsed
        .astimezone(
            timezone.utc,
        )
    )


def parse_profit(
    details: str,
) -> (
    Decimal | None
):
    match = (
        profit_pattern
        .search(
            details,
        )
    )

    if (
        match
        is None
    ):
        return None

    try:
        return Decimal(
            match
            .group(
                1,
            )
        )

    except ValueError:
        return None


def _last_equity_at_or_before(
    snapshots: list[
        tuple[
            datetime,
            Decimal,
        ]
    ],
    moment: datetime,
) -> (
    Decimal | None
):
    latest = None

    for ts, equity in sorted(
        snapshots,
        key=(
            lambda item: (
                item[
                    0
                ]
            )
        ),
    ):
        if (
            ts
            <= moment
        ):
            latest = (
                equity
            )

    return latest


@dataclass(slots=True)
class EquityHistoryService:
    operation_log_repository: (
        Any | None
    ) = None

    money_movement_repository: (
        Any | None
    ) = None

    broker_cash_flow_repository: (
        Any | None
    ) = None

    def build(
        self,
        current_equity: Decimal,
        days: int = 7,
        current_equity_by_currency: (
            dict[
                str,
                Decimal,
            ]
            | None
        ) = None,
        account_currency_by_id: (
            dict[
                str,
                str,
            ]
            | None
        ) = None,
        snapshots_by_currency: (
            dict[
                str,
                list[
                    tuple[
                        datetime,
                        Decimal,
                    ]
                ],
            ]
            | None
        ) = None,

        first_snapshot_by_currency: (
            dict[
                str,
                tuple[
                    datetime,
                    Decimal,
                ],
            ]
            | None
        ) = None,
    ) -> dict:
        if (
            days
            not in allowed_days
        ):
            days = 7

        now = (
            datetime
            .now(
                timezone.utc,
            )
        )

        since = (
            now
            - timedelta(
                days=days,
            )
        )

        changes = (
            self
            ._collect_changes(
                since=since,

                account_currency_by_id=(
                    account_currency_by_id
                ),
            )
        )

        points = (
            self
            ._build_points(
                current_equity=(
                    current_equity
                ),

                changes=changes,

                since=since,

                now=now,
            )
        )

        today_start = (
            now
            .replace(
                hour=0,

                minute=0,

                second=0,

                microsecond=0,
            )
        )

        profit_today_by_currency: dict[str, Decimal] = {}

        movements_today_by_currency: dict[str, Decimal] = {}

        for (
            ts,
            kind,
            value,
            currency,
        ) in changes:
            if (
                ts
                < today_start
            ):
                continue

            if (
                kind
                == "profit"
            ):
                profit_today_by_currency[
                    currency
                ] = (
                    profit_today_by_currency
                    .get(
                        currency,
                        Decimal(
                            "0",
                        ),
                    )
                    + value
                )

            elif (
                kind
                == "movement"
            ):
                movements_today_by_currency[
                    currency
                ] = (
                    movements_today_by_currency
                    .get(
                        currency,
                        Decimal(
                            "0",
                        ),
                    )
                    + value
                )

        movements_today = sum(
            (
                value

                for (
                    _currency,
                    value,
                )

                in (
                    movements_today_by_currency
                    .items()
                )
            ),

            Decimal(
                "0",
            ),
        )

        current_by_currency = {}

        if (
            current_equity_by_currency
        ):
            current_by_currency = (
                dict(
                    current_equity_by_currency,
                )
            )

        elif (
            snapshots_by_currency
        ):
            current_by_currency = {
                currency: (
                    sorted(
                        snapshots,
                        key=(
                            lambda item: (
                                item[
                                    0
                                ]
                            )
                        ),
                    )[
                        -1
                    ][
                        1
                    ]
                )

                for currency, snapshots
                in (
                    snapshots_by_currency
                    .items()
                )
            }

        day_start_by_currency = {}

        if (
            current_by_currency
            and snapshots_by_currency
        ):
            for (
                currency
            ) in (
                current_by_currency
            ):
                snapshots = (
                    snapshots_by_currency
                    .get(
                        currency,
                    )
                )

                if (
                    not snapshots
                ):
                    continue
                equity_at_day_start = (
                    _last_equity_at_or_before(
                        snapshots=(
                            snapshots
                        ),

                        moment=(
                            today_start
                        ),
                    )
                )

                if (
                    equity_at_day_start
                    is not None
                ):
                    day_start_by_currency[
                        currency
                    ] = (
                        equity_at_day_start
                    )

        if (
            current_by_currency
        ):
            pnl_today = (
                Decimal(
                    "0",
                )
            )

            equity_day_start = (
                Decimal(
                    "0",
                )
            )

            for (
                currency,

                current_equity_currency,
            ) in (
                current_by_currency
                .items()
            ):
                day_start_equity = (
                    day_start_by_currency
                    .get(
                        currency,
                    )
                )

                if (
                    day_start_equity
                    is None
                ):
                    currency_pnl = (
                        profit_today_by_currency
                        .get(
                            currency,

                            Decimal(
                                "0",
                            ),
                        )
                    )

                    equity_day_start += (
                        current_equity_currency
                        - currency_pnl
                        - movements_today_by_currency
                        .get(
                            currency,

                            Decimal(
                                "0",
                            ),
                        )
                    )

                else:
                    currency_pnl = (
                        current_equity_currency
                        - day_start_equity
                        - movements_today_by_currency
                        .get(
                            currency,

                            Decimal(
                                "0",
                            ),
                        )
                    )

                    equity_day_start += (
                        day_start_equity
                    )
                pnl_today += (
                    currency_pnl
                )

        else:
            pnl_today = sum(
                (
                    profit_today_by_currency
                    .values()
                ),

                Decimal(
                    "0",
                ),
            )

            equity_day_start = (
                current_equity
                - pnl_today
                - movements_today
            )

        pnl_today_percent = None

        if (
            equity_day_start
            > 0
        ):
            pnl_today_percent = float(
                pnl_today
                / equity_day_start
                * Decimal(
                    "100"
                )
            )

        pnl_total = None

        pnl_total_percent = None

        if (
            first_snapshot_by_currency
        ):
            first_timestamp = min(
                (
                    item[
                        0
                    ]

                    for item
                    in (
                        first_snapshot_by_currency
                        .values()
                    )
                ),
            )

            equity_start = sum(
                (
                    item[
                        1
                    ]

                    for item
                    in (
                        first_snapshot_by_currency
                        .values()
                    )
                ),

                Decimal(
                    "0",
                ),
            )

            flows_total = (
                Decimal(
                    "0",
                )
            )

            if (
                self
                .broker_cash_flow_repository
                is not None
            ):
                for flow in (
                    self
                    .broker_cash_flow_repository
                    .get_since(
                        since=(
                            first_timestamp
                            .isoformat()
                        ),
                    )
                ):
                    flows_total += (
                        flow
                        .payment
                    )

            movements_total = (
                Decimal(
                    "0",
                )
            )

            if (
                self
                .money_movement_repository
                is not None
            ):
                for movement in (
                    self
                    .money_movement_repository
                    .get_since(
                        since=(
                            first_timestamp
                            .isoformat()
                        ),
                    )
                ):
                    movements_total += (
                        movement
                        .amount
                    )

            pnl_total = (
                current_equity
                - equity_start
                - movements_total
                - flows_total
            )

            if (
                equity_start
                > 0
            ):
                pnl_total_percent = float(
                    pnl_total
                    / equity_start
                    * Decimal(
                        "100"
                    )
                )

        response = {
            "days":
                days,

            "equity":
                float(
                    current_equity,
                ),

            "points":
                points,

            "pnl_today":
                float(
                    pnl_today,
                ),

            "pnl_today_percent":
                pnl_today_percent,

            "pnl_total":
                (
                    float(
                        pnl_total,
                    )

                    if (
                        pnl_total
                        is not None
                    )

                    else None
                ),

            "pnl_total_percent":
                pnl_total_percent,

            "updated_at":
                (
                    now
                    .isoformat()
                ),
        }

        snapshots_by_currency_window = {}

        if snapshots_by_currency:
            snapshots_by_currency_window = {
                currency: [
                    snapshot

                    for snapshot
                    in sorted(
                        snapshots,
                        key=(
                            lambda item: (
                                item[
                                    0
                                ]
                            )
                        ),
                    )

                    if (
                        snapshot[
                            0
                        ]
                        >= since
                    )
                ]

                for currency, snapshots
                in snapshots_by_currency.items()
            }

            snapshots_by_currency_window = {
                currency: snapshots

                for currency, snapshots
                in snapshots_by_currency_window.items()

                if snapshots
            }

        if snapshots_by_currency_window:
            sorted_currencies = (
                sorted(
                    snapshots_by_currency_window,
                )
            )

            points_by_currency = {}

            for currency in sorted_currencies:
                snapshots = (
                    snapshots_by_currency_window[
                        currency
                    ]
                )

                currency_equity = (
                    (
                        current_equity_by_currency
                        or {}
                    ).get(
                        currency,
                    )
                )

                if (
                    currency_equity
                    is None
                ):
                    currency_equity = (
                        snapshots[
                            -1
                        ][
                            1
                        ]
                    )

                reconstructed = (
                    self
                    ._build_points(
                        current_equity=(
                            currency_equity
                        ),

                        changes=(
                            changes
                        ),

                        since=(
                            since
                        ),

                        now=(
                            now
                        ),

                        currency=(
                            currency
                        ),
                    )
                )

                first_snapshot_ts = (
                    snapshots[
                        0
                    ][
                        0
                    ]
                )

                merged_points = [
                    point

                    for point
                    in reconstructed

                    if (
                        (
                            _parse_timestamp(
                                point[
                                    "ts"
                                ],
                            )

                            or now
                        )
                        < first_snapshot_ts
                    )
                ]

                merged_points.extend(
                    self
                    ._points_from_snapshots(
                        snapshots=(
                            snapshots
                        ),

                        now=now,
                        current_equity=currency_equity,
                    )
                )

                points_by_currency[
                    currency
                ] = (
                    merged_points
                )

            response[
                "points_by_currency"
            ] = (
                points_by_currency
            )

            response[
                "equity_by_currency"
            ] = {
                currency: float(
                    (current_equity_by_currency or {}).get(
                        currency,
                        snapshots_by_currency_window[currency][-1][1],
                    ),
                )

                for currency
                in sorted_currencies
            }

        elif current_equity_by_currency:
            sorted_equity = (
                sorted(
                    current_equity_by_currency.items(),
                )
            )

            points_by_currency = {
                currency: (
                    self
                    ._build_points(
                        current_equity=(
                            currency_equity
                        ),

                        changes=(
                            changes
                        ),

                        since=(
                            since
                        ),

                        now=(
                            now
                        ),

                        currency=(
                            currency
                        ),
                    )
                )

                for currency, currency_equity
                in sorted_equity
            }

            response[
                "equity_by_currency"
            ] = {
                currency: float(
                    currency_equity,
                )

                for currency, currency_equity
                in sorted_equity
            }

            response[
                "points_by_currency"
            ] = (
                points_by_currency
            )

        return response

    def snapshot_points(
        self,
        snapshots: list[
            tuple[
                datetime,
                Decimal,
            ]
        ],
        now: datetime,
        current_equity: Decimal | None = None,
    ) -> list[dict]:
        return (
            self
            ._points_from_snapshots(
                snapshots=(
                    snapshots
                ),

                now=now,
                current_equity=current_equity,
            )
        )

    def pnl_today_by_account(
        self,
        current_equity_by_account: (
            dict[
                str,
                Decimal,
            ]
            | None
        ) = None,

        snapshots_by_account: (
            dict[
                str,
                list[
                    tuple[
                        datetime,
                        Decimal,
                    ]
                ],
            ]
            | None
        ) = None,
    ) -> (
        dict[
            str,
            Decimal,
        ]
    ):
        if (
            self
            .operation_log_repository
            is None
        ):
            return {}

        now = (
            datetime
            .now(
                timezone.utc,
            )
        )

        today_start = (
            now
            .replace(
                hour=0,

                minute=0,

                second=0,

                microsecond=0,
            )
        )

        result: dict[
            str,
            Decimal,
        ] = {}

        events = (
            self
            .operation_log_repository
            .get_since(
                since=(
                    today_start
                    .isoformat()
                ),

                event_types=[
                    "SELL",
                ],
            )
        )

        for event in events:
            profit = (
                parse_profit(
                    event
                    .details,
                )
            )

            if (
                profit
                is None
            ):
                continue
            key = (
                event
                .trading_account_id
                or ""
            )

            result[
                key
            ] = (
                result.get(
                    key,

                    Decimal(
                        "0",
                    ),
                )
                + profit
            )

        if (
            snapshots_by_account
            and current_equity_by_account
        ):
            movements_today_by_account: dict[str, Decimal] = {}

            if (
                self
                .money_movement_repository
                is not None
            ):
                movements = (
                    self
                    .money_movement_repository
                    .get_since(
                        since=(
                            today_start
                            .isoformat()
                        ),
                    )
                )

                for movement in movements:
                    ts = (
                        _parse_timestamp(
                            movement
                            .created_at,
                        )
                    )

                    if (
                        ts
                        is None
                        or ts
                        < today_start
                    ):
                        continue
                    movement_key = (
                        movement
                        .trading_account_id
                        or ""
                    )

                    movements_today_by_account[
                        movement_key
                    ] = (
                        movements_today_by_account
                        .get(
                            movement_key,

                            Decimal(
                                "0",
                            ),
                        )
                        + movement
                        .amount
                    )

            if self.broker_cash_flow_repository is not None:
                flows = self.broker_cash_flow_repository.get_since(
                    since=today_start.isoformat(),
                )
                for flow in flows:
                    ts = _parse_timestamp(flow.occurred_at)
                    if ts is None or not today_start <= ts <= now:
                        continue
                    movements_today_by_account[flow.trading_account_id] = (
                        movements_today_by_account.get(
                            flow.trading_account_id,
                            Decimal("0"),
                        )
                        + flow.payment
                    )

            for (
                account_id,

                snapshots,
            ) in (
                snapshots_by_account
                .items()
            ):
                current_equity_account = (
                    current_equity_by_account
                    .get(
                        account_id,
                    )
                )

                if (
                    current_equity_account
                    is None
                ):
                    continue
                equity_at_day_start = (
                    _last_equity_at_or_before(
                        snapshots=(
                            snapshots
                        ),

                        moment=(
                            today_start
                        ),
                    )
                )

                if (
                    equity_at_day_start
                    is None
                ):
                    continue
                result[
                    account_id
                ] = (
                    current_equity_account
                    - equity_at_day_start
                    - movements_today_by_account
                    .get(
                        account_id,

                        Decimal(
                            "0",
                        ),
                    )
                )

        return result

    def _collect_changes(
        self,
        since: datetime,
        account_currency_by_id: (
            dict[
                str,
                str,
            ]
            | None
        ) = None,
    ) -> list[
        tuple[
            datetime,
            str,
            Decimal,
            str,
        ]
    ]:
        changes = []

        currency_by_account = (
            account_currency_by_id
            or {}
        )

        if (
            self
            .operation_log_repository
            is not None
        ):
            events = (
                self
                .operation_log_repository
                .get_since(
                    since=(
                        since
                        .isoformat()
                    ),

                    event_types=[
                        "SELL",
                    ],
                )
            )

            for event in events:
                profit = (
                    parse_profit(
                        event
                        .details,
                    )
                )

                ts = (
                    _parse_timestamp(
                        event
                        .created_at,
                    )
                )

                if (
                    profit
                    is None
                    or ts
                    is None
                ):
                    continue

                changes.append(
                    (
                        ts,

                        "profit",

                        profit,

                        currency_by_account.get(
                            event
                            .trading_account_id,

                            "RUB",
                        ),
                    )
                )

        if (
            self
            .money_movement_repository
            is not None
        ):
            movements = (
                self
                .money_movement_repository
                .get_since(
                    since=(
                        since
                        .isoformat()
                    ),
                )
            )

            for movement in movements:
                ts = (
                    _parse_timestamp(
                        movement
                        .created_at,
                    )
                )

                if (
                    ts
                    is None
                ):
                    continue

                changes.append(
                    (
                        ts,

                        "movement",

                        movement
                        .amount,

                        currency_by_account.get(
                            movement
                            .trading_account_id,

                            "RUB",
                        ),
                    )
                )

        if (
            self
            .broker_cash_flow_repository
            is not None
        ):
            flows = (
                self
                .broker_cash_flow_repository
                .get_since(
                    since=(
                        since
                        .isoformat()
                    ),
                )
            )

            for flow in flows:
                ts = (
                    _parse_timestamp(
                        flow
                        .occurred_at,
                    )
                )

                if (
                    ts
                    is None
                ):
                    continue

                changes.append(
                    (
                        ts,

                        "movement",

                        flow
                        .payment,

                        (
                            flow
                            .currency

                            or "RUB"
                        ),
                    )
                )

        changes.sort(
            key=(
                lambda item: (
                    item[
                        0
                    ]
                )
            ),
        )

        return changes

    def _build_points(
        self,
        current_equity: Decimal,
        changes: list[
            tuple[
                datetime,
                str,
                Decimal,
                str,
            ]
        ],
        since: datetime,
        now: datetime,
        currency: (
            str | None
        ) = None,
    ) -> list[dict]:
        if (
            currency
            is not None
        ):
            changes = [
                change

                for change
                in changes

                if (
                    change[
                        3
                    ]
                    == currency
                )
            ]

        total = sum(
            (
                value

                for (
                    _ts,
                    _kind,
                    value,
                    _currency,
                )

                in changes
            ),

            Decimal("0"),
        )

        equity = (
            current_equity
            - total
        )

        points = [
            {
                "ts": (
                    since
                    .isoformat()
                ),

                "equity": float(
                    equity
                ),
            },
        ]

        for (
            ts,
            _kind,
            value,
            _currency,
        ) in changes:
            equity += value

            points.append(
                {
                    "ts": (
                        ts
                        .isoformat()
                    ),

                    "equity": float(
                        equity
                    ),
                }
            )

        points.append(
            {
                "ts": (
                    now
                    .isoformat()
                ),

                "equity": float(
                    current_equity
                ),
            }
        )

        return points

    def _points_from_snapshots(
        self,
        snapshots: list[
            tuple[
                datetime,
                Decimal,
            ]
        ],
        now: datetime,
        current_equity: Decimal | None = None,
    ) -> list[dict]:
        if not snapshots:
            return []

        points = []

        for (
            ts,
            value,
        ) in snapshots:
            points.append(
                {
                    "ts": (
                        ts
                        .isoformat()
                    ),

                    "equity": float(
                        value
                    ),
                }
            )

        points.append(
            {
                "ts": (
                    now
                    .isoformat()
                ),

                "equity": float(
                    current_equity
                    if current_equity is not None
                    else snapshots[-1][1]
                ),
            }
        )

        return points
