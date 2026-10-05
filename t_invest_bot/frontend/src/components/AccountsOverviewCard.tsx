import { useState } from "react"
import { TradingAccountDetails } from "./TradingOverviewCard"

import type {
    AccountsOverview,
    ActiveSession,
    OverviewAccount,
    OverviewAsset,
} from "../types"


function formatMoney(
    value: number | null
): string {
    if (
        value
        === null
    ) {
        return "—"
    }

    return value
        .toLocaleString(
            "ru-RU",
            {
                maximumFractionDigits:
                    2,
            }
        )
}


function formatChange(
    value: number | null
): string {
    if (
        value
        === null
    ) {
        return "—"
    }

    const sign = (
        value
        > 0
            ? "+"
            : ""
    )

    return (
        sign
        + value
            .toLocaleString(
                "ru-RU",
                {
                    maximumFractionDigits:
                        2,
                }
            )
    )
}


function formatQuantity(
    asset: OverviewAsset
): string {
    if (
        asset.quantity
        === null
    ) {
        return "—"
    }

    return asset.quantity
        .toLocaleString(
            "ru-RU",
            {
                maximumFractionDigits:
                    asset
                        .quantity_precision,
            }
        )
}


function Sparkline({
    points,
}: {
    points: number[]
}) {
    if (
        points.length
        < 2
    ) {
        return null
    }

    const width = 120

    const height = 34

    const min = (
        Math
        .min(
            ...points
        )
    )

    const max = (
        Math
        .max(
            ...points
        )
    )

    const span = (
        max
        - min
        || 1
    )

    const coords = (
        points
        .map(
            (
                value,
                index
            ) => {
                const x = (
                    index
                    / (
                        points.length
                        - 1
                    )
                    * width
                )

                const y = (
                    height
                    - (
                        (
                            value
                            - min
                        )
                        / span
                    )
                    * (
                        height
                        - 4
                    )
                    - 2
                )

                return `${x.toFixed(1)},${y.toFixed(1)}`
            }
        )
        .join(
            " "
        )
    )

    const rising = (
        points[
            points.length
            - 1
        ]
        >= points[0]
    )

    return (
        <svg
            width={
                width
            }

            height={
                height
            }

            viewBox={
                `0 0 ${width} ${height}`
            }

            style={{
                display:
                "block",
            }}
        >
            <polyline
                points={
                    coords
                }

                fill={
                    "none"
                }

                stroke={
                    rising
                        ? "var(--profit)"
                        : "var(--loss)"
                }

                strokeWidth={
                    1.5
                }
            />
        </svg>
    )
}


function AccountBlock({
    account,
}: {
    account: OverviewAccount
}) {
    const series = (
        (
            account
            .balance_series
            ?? []
        ).map(
            point => (
                point.equity
            )
        )
    )

    return (
        <div
            style={{
                background:
                "var(--card)",

                borderRadius:
                16,

                padding:
                "14px 16px",

                marginBottom:
                12,
            }}
        >
            <div
                style={{
                    display:
                    "flex",

                    alignItems:
                    "center",

                    gap:
                    12,
                }}
            >
                <div
                    style={{
                        width:
                        40,

                        height:
                        40,

                        borderRadius:
                        "50%",

                        display:
                        "flex",

                        alignItems:
                        "center",

                        justifyContent:
                        "center",

                        background: (
                            account.enabled
                                ? "var(--accent)"
                                : "var(--card-soft)"
                        ),

                        color: (
                            account.enabled
                                ? "#111111"
                                : "var(--text-muted)"
                        ),

                        fontWeight:
                        700,

                        flexShrink:
                        0,
                    }}
                >
                    {
                        (
                            account
                                .name
                                .trim()
                                .charAt(
                                    0
                                )
                                .toUpperCase()

                            || "С"
                        )
                    }
                </div>

                <div
                    style={{
                        flex:
                        1,

                        minWidth:
                        0,
                    }}
                >
                    <div
                        style={{
                            fontWeight:
                            700,
                        }}
                    >
                        {
                            account
                                .name
                        }
                    </div>

                    <div
                        style={{
                            fontSize:
                            12,

                            color:
                            "var(--text-muted)",
                        }}
                    >
                        {
                            account
                                .broker
                        }

                        {" · "}

                        {
                            account
                                .mode
                                === "live"
                                ? "LIVE"
                                : "SANDBOX"
                        }

                        {" · "}

                        {
                            account
                                .currency
                        }
                    </div>
                </div>

                <div
                    style={{
                        textAlign:
                        "right",
                    }}
                >
                    <div
                        style={{
                            fontSize:
                            11,

                            color:
                            "var(--text-muted)",
                        }}
                    >
                        Стоимость активов
                    </div>

                    <div
                        style={{
                            fontWeight:
                            700,

                            fontSize:
                            16,
                        }}
                    >
                        {
                            formatMoney(
                                account.equity
                            )
                        }

                        {" "}

                        {
                            account
                                .currency
                        }
                    </div>
                </div>
            </div>

            <div
                style={{
                    display:
                    "flex",

                    alignItems:
                    "flex-end",

                    justifyContent:
                    "space-between",

                    gap:
                    12,

                    marginTop:
                    10,
                }}
            >
                <div
                    style={{
                        display:
                        "flex",

                        gap:
                        16,

                        fontSize:
                        12,

                        color:
                        "var(--text-muted)",
                    }}
                >
                    <div>
                        <div>
                            Доступный баланс
                        </div>

                        <b
                            style={{
                                color:
                                "var(--text)",
                            }}
                        >
                            {
                                formatMoney(
                                    account.available
                                )
                            }

                            {" "}

                            {
                                account
                                    .currency
                            }
                        </b>
                    </div>

                    <div>
                        <div>
                            Используется
                        </div>

                        <b
                            style={{
                                color:
                                "var(--text)",
                            }}
                        >
                            {
                                formatMoney(
                                    account.invested
                                )
                            }

                            {" "}

                            {
                                account
                                    .currency
                            }
                        </b>
                    </div>
                </div>

                <Sparkline
                    points={
                        series
                    }
                />
            </div>
        </div>
    )
}


function ActiveAccountBlock({
    account,
    sessions,
    onOpenTicker,
}: {
    account: OverviewAccount
    sessions: ActiveSession[]
    onOpenTicker: (ticker: string) => void
}) {
    const [expanded, setExpanded] = useState(false)

    return (
        <div style={{ marginBottom: 12 }}>
            <button
                type="button"
                aria-expanded={expanded}
                onClick={() => setExpanded(current => !current)}
                style={{
                    display: "block",
                    width: "100%",
                    padding: 0,
                    border: "none",
                    background: "transparent",
                    color: "var(--text)",
                    textAlign: "left",
                    cursor: "pointer",
                }}
            >
                <AccountBlock account={account} />
                <div style={{ textAlign: "right", fontSize: 12, marginTop: -8 }}>
                    {expanded ? "Скрыть активы и сессии ▴" : "Показать активы и сессии ▾"}
                </div>
            </button>
            {expanded && <>
                <TradingAccountDetails account={account} sessions={sessions} onOpenTicker={onOpenTicker} />
                <AssetsCard overview={{ accounts: [account] }} />
            </>}
        </div>
    )
}

export function OverviewAccountsCard({
    overview,
    sessions = [],
    onOpenTicker,
}: {
    overview: AccountsOverview | null
    sessions?: ActiveSession[]
    onOpenTicker: (ticker: string) => void
}) {
    if (
        overview
        === null
    ) {
        return (
            <div
                style={{
                    color:
                    "var(--text-muted)",

                    fontSize:
                    13,
                }}
            >
                Загрузка...
            </div>
        )
    }

    if (
        overview
        .accounts
        .length
        === 0
    ) {
        return (
            <div
                style={{
                    color:
                    "var(--text-muted)",

                    fontSize:
                    13,
                }}
            >
                Счета пока не добавлены.
            </div>
        )
    }

    return (
        <div>
            {
                overview
                .accounts
                .map(
                    account => (
                        <ActiveAccountBlock
                            key={account.id}
                            account={account}
                            sessions={sessions}
                            onOpenTicker={onOpenTicker}
                        />
                    )
                )
            }
        </div>
    )
}


export function AssetsCard({
    overview,
}: {
    overview: AccountsOverview | null
}) {
    if (
        overview
        === null
    ) {
        return (
            <div
                style={{
                    color:
                    "var(--text-muted)",

                    fontSize:
                    13,
                }}
            >
                Загрузка...
            </div>
        )
    }

    return (
        <div>
            {
                overview
                .accounts
                .map(
                    account => (
                        <div
                            key={
                                account.id
                            }

                            style={{
                                marginBottom:
                                18,
                            }}
                        >
                            <div
                                style={{
                                    display:
                                    "flex",

                                    justifyContent:
                                    "space-between",

                                    alignItems:
                                    "baseline",

                                    marginBottom:
                                    8,
                                }}
                            >
                                <b>
                                    {
                                        account
                                            .name
                                    }
                                </b>

                                <span
                                    style={{
                                        fontSize:
                                        12,

                                        color:
                                        "var(--text-muted)",
                                    }}
                                >
                                    {
                                        account
                                            .currency
                                    }
                                </span>
                            </div>

                            {
                                account
                                .assets
                                .map(
                                    asset => {
                                        const changeUp = (
                                            (
                                                asset.change_24h
                                                ?? 0
                                            )
                                            >= 0
                                        )

                                        return (
                                            <div
                                                key={
                                                    asset.ticker
                                                }

                                                style={{
                                                    display:
                                                    "grid",

                                                    gridTemplateColumns:
                                                    "1fr auto auto",

                                                    gap:
                                                    "4px 14px",

                                                    alignItems:
                                                    "baseline",

                                                    background:
                                                    "var(--card)",

                                                    borderRadius:
                                                    14,

                                                    padding:
                                                    "12px 14px",

                                                    marginBottom:
                                                    8,
                                                }}
                                            >
                                                <div>
                                                    <b>
                                                        {
                                                            asset.ticker
                                                        }
                                                    </b>

                                                    <div
                                                        style={{
                                                            fontSize:
                                                            11,

                                                            color:
                                                            "var(--text-muted)",
                                                        }}
                                                    >
                                                        {
                                                            asset.kind
                                                                === "currency"
                                                                ? "валюта"
                                                                : "инструмент"
                                                        }
                                                    </div>
                                                </div>

                                                <div
                                                    style={{
                                                        textAlign:
                                                        "right",
                                                    }}
                                                >
                                                    <div
                                                        style={{
                                                            fontSize:
                                                            11,

                                                            color:
                                                            "var(--text-muted)",
                                                        }}
                                                    >
                                                        Количество
                                                    </div>

                                                    <div>
                                                        {
                                                            formatQuantity(
                                                                asset
                                                            )
                                                        }
                                                    </div>
                                                </div>

                                                <div
                                                    style={{
                                                        textAlign:
                                                        "right",
                                                    }}
                                                >
                                                    <div
                                                        style={{
                                                            fontSize:
                                                            11,

                                                            color:
                                                            "var(--text-muted)",
                                                        }}
                                                    >
                                                        Стоимость
                                                    </div>

                                                    <b>
                                                        {
                                                            formatMoney(
                                                                asset.value
                                                            )
                                                        }
                                                    </b>

                                                    <div
                                                        style={{
                                                            fontSize:
                                                            11,

                                                            color: (
                                                                changeUp
                                                                    ? "var(--profit)"
                                                                    : "var(--loss)"
                                                            ),
                                                        }}
                                                    >
                                                        {
                                                            formatChange(
                                                                asset.change_24h
                                                            )
                                                        }

                                                        {" ("}

                                                        {
                                                            formatChange(
                                                                asset.change_24h_percent
                                                            )
                                                        }

                                                        {"%)"}
                                                    </div>
                                                </div>
                                            </div>
                                        )
                                    }
                                )
                            }
                        </div>
                    )
                )
            }
        </div>
    )
}
