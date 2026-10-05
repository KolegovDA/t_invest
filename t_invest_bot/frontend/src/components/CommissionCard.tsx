import {
    useEffect,
    useState,
} from "react"

import {
    getCommissionSummary,
} from "../api"

import type {
    CommissionSummary,
} from "../types"


function formatMoney(
    value: string
): string {
    const numeric =
        Number(value)

    if (
        Number.isNaN(
            numeric
        )
    ) {
        return value
    }

    return (
        numeric.toLocaleString(
            "ru-RU",
            {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
            }
        )
        + " ₽"
    )
}


function formatDateTime(
    iso: string
): string {
    const date = (
        new Date(
            iso
        )
    )

    if (
        Number.isNaN(
            date.getTime()
        )
    ) {
        return iso
    }

    return (
        date
        .toLocaleString(
            "ru-RU",
            {
                day: "2-digit",
                month: "2-digit",

                hour: "2-digit",
                minute: "2-digit",
            }
        )
    )
}


export function CommissionCard() {
    const [
        summary,
        setSummary,
    ] = useState<
        CommissionSummary | null
    >(null)

    const [
        error,
        setError,
    ] = useState<
        string | null
    >(null)


    useEffect(
        () => {
            let cancelled = false


            async function load() {
                try {
                    const data = (
                        await getCommissionSummary()
                    )

                    if (
                        !cancelled
                    ) {
                        setSummary(
                            data
                        )

                        setError(
                            null
                        )
                    }

                } catch (loadError) {
                    if (
                        !cancelled
                    ) {
                        setError(
                            loadError instanceof Error
                                ? loadError.message
                                : String(
                                    loadError
                                )
                        )
                    }
                }
            }


            load()

            const timer = (
                setInterval(
                    load,

                    60000
                )
            )

            return () => {
                cancelled = true

                clearInterval(
                    timer
                )
            }
        },

        []
    )


    const balanceNumeric = (
        summary
            ? Number(
                summary.balance
            )
            : null
    )

    const balanceColor = (
        balanceNumeric
        === null
            ? "var(--text)"
            : balanceNumeric
            < 0
                ? "var(--loss)"
                : "var(--text)"
    )

    const platforms = (
        summary
            ? Object.entries(
                summary.by_platform
            )
            : []
    )

    return (
        <div
            style={{
                background:
                "var(--card)",

                borderRadius:
                14,

                padding:
                13,

                marginTop:
                10,

                color:
                "var(--text)",
            }}
        >
            <h3
                style={{
                    marginTop:
                    0,

                    marginBottom:
                    10,
                }}
            >
                Комиссия сервиса
            </h3>

            {error && (
                <div
                    style={{
                        padding:
                        10,

                        borderRadius:
                        10,

                        background:
                        "var(--loss-soft)",

                        color:
                        "var(--loss)",

                        fontSize:
                        13,

                        wordBreak:
                        "break-word",
                    }}
                >
                    {
                        error
                    }
                </div>
            )}

            {summary && (
                <>
                    <div
                        style={{
                            display:
                            "flex",

                            alignItems:
                            "baseline",

                            gap:
                            8,
                        }}
                    >
                        <span
                            style={{
                                fontSize:
                                28,

                                fontWeight:
                                700,

                                color:
                                balanceColor,
                            }}
                        >
                            {
                                formatMoney(
                                    summary.balance
                                )
                            }
                        </span>

                        {
                            summary
                                .forced_drain
                            && (
                                <span
                                    style={{
                                        fontSize:
                                        11,

                                        padding:
                                        "3px 8px",

                                        borderRadius:
                                        999,

                                        background:
                                        "var(--loss-soft)",

                                        color:
                                        "var(--loss)",

                                        fontWeight:
                                        600,
                                    }}
                                >
                                    Принудительная сушка
                                </span>
                            )
                        }
                    </div>

                    <div
                        style={{
                            marginTop:
                            4,

                            fontSize:
                            12,

                            color:
                            "var(--text-muted)",
                        }}
                    >
                        ЛК-баланс. Комиссия:
                        {" "}

                        {
                            summary
                                .default_percent
                        }
                        %

                        {
                            platforms.map(
                                ([
                                    platform,
                                    percent,
                                ]) => (
                                    " · "
                                    + platform
                                    + ": "
                                    + percent
                                    + "%"
                                )
                            )
                        }
                    </div>

                    <div
                        style={{
                            marginTop:
                            6,

                            fontSize:
                            11,

                            color:
                            "var(--text-dim)",
                        }}
                    >
                        Списание с чистой прибыли
                        каждой закрытой SELL-сделки.
                        При отрицательном балансе новые
                        сетки запрещены.
                    </div>

                    {
                        summary
                            .charges
                            .length
                        > 0
                        && (
                            <div
                                style={{
                                    marginTop:
                                    10,

                                    display:
                                    "grid",

                                    gap:
                                    6,
                                }}
                            >
                                {
                                    summary.charges.map(
                                        charge => (
                                            <div
                                                key={
                                                    charge.id
                                                }

                                                style={{
                                                    display:
                                                    "flex",

                                                    justifyContent:
                                                    "space-between",

                                                    gap:
                                                    10,

                                                    padding:
                                                    "8px 10px",

                                                    borderRadius:
                                                    10,

                                                    background:
                                                    "var(--card-soft)",

                                                    fontSize:
                                                    12,
                                                }}
                                            >
                                                <div
                                                    style={{
                                                        minWidth:
                                                        0,
                                                    }}
                                                >
                                                    <div
                                                        style={{
                                                            fontWeight:
                                                            600,
                                                        }}
                                                    >
                                                        {
                                                            charge.ticker
                                                            ?? charge.broker
                                                        }

                                                        {
                                                            charge.level_index
                                                            !== null
                                                                ? ` · ур. ${charge.level_index}`
                                                                : ""
                                                        }
                                                    </div>

                                                    <div
                                                        style={{
                                                            marginTop:
                                                            2,

                                                            color:
                                                            "var(--text-muted)",
                                                        }}
                                                    >
                                                        {
                                                            formatDateTime(
                                                                charge.created_at
                                                            )
                                                        }

                                                        {" · "}

                                                        {
                                                            formatMoney(
                                                                charge.trade_profit
                                                            )
                                                        }

                                                        {" · "}

                                                        {
                                                            charge.percent
                                                        }
                                                        %
                                                    </div>
                                                </div>

                                                <div
                                                    style={{
                                                        textAlign:
                                                        "right",

                                                        fontWeight:
                                                        700,

                                                        color:
                                                        "var(--loss)",

                                                        flexShrink:
                                                        0,
                                                    }}
                                                >
                                                    −{
                                                        formatMoney(
                                                            charge.amount
                                                        )
                                                    }

                                                    <div
                                                        style={{
                                                            marginTop:
                                                            2,

                                                            fontSize:
                                                            11,

                                                            fontWeight:
                                                            400,

                                                            color:
                                                            "var(--text-dim)",
                                                        }}
                                                    >
                                                        бал. {
                                                            formatMoney(
                                                                charge.balance_after
                                                            )
                                                        }
                                                    </div>
                                                </div>
                                            </div>
                                        )
                                    )
                                }
                            </div>
                        )
                    }

                    {
                        summary
                            .charges
                            .length
                        === 0
                        && (
                            <div
                                style={{
                                    marginTop:
                                    10,

                                    fontSize:
                                    12,

                                    color:
                                    "var(--text-dim)",
                                }}
                            >
                                Списаний ещё не было.
                            </div>
                        )
                    }
                </>
            )}
        </div>
    )
}
