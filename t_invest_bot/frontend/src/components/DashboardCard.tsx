import {
    useEffect,
    useId,
    useState,
} from "react"

import {
    getDashboardHistory,
} from "../api"

import { defaultPlatformColors, getStoredPlatformColors } from "../theme"
import type { PlatformColors } from "../theme"

import type {
    Dashboard,
    DashboardHistory,
    EquityPoint,
} from "../types"


type Props = {
    dashboard: Dashboard
}


const periodOptions = [
    {
        label: "7D",

        days: 7,
    },

    {
        label: "30D",

        days: 30,
    },

    {
        label: "90D",

        days: 90,
    },

    {
        label: "180D",

        days: 180,
    },
]


function formatEquity(
    value: number
): string {
    return (
        value.toLocaleString(
            "ru-RU",
            {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
            }
        )
    )
}


function formatSigned(
    value: number
): string {
    return (
        (
            value < 0
                ? "-"
                : "+"
        )
        + Math.abs(
            value
        ).toLocaleString(
            "ru-RU",
            {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
            }
        )
    )
}


function formatSignedPercent(
    value: number
): string {
    return (
        (
            value < 0
                ? ""
                : "+"
        )
        + value.toFixed(
            2
        )
        + "%"
    )
}


function formatUpdatedAt(
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
        return ""
    }

    const isoText = (
        date
        .toISOString()
    )

    return (
        isoText
        .slice(
            0,
            10
        )
        + " "
        + isoText
        .slice(
            11,
            16
        )
        + " (UTC)"
    )
}


function EquityChart({
    series,
    days,
    updatedAt,
}: {
    days: number
    updatedAt: string
    series: Array<{
        label: string
        points: EquityPoint[]
        color: string
    }>
}) {
    const [zoom, setZoom] = useState(1)
    const [verticalZoom, setVerticalZoom] = useState(1)
    const [offset, setOffset] = useState(0)
    const [showScale, setShowScale] = useState(false)
    const clipId = useId()
    const width = 640
    const height = 220
    const paddingLeft = 72
    const paddingRight = 8
    const paddingTop = 12
    const paddingBottom = 32
    const plotWidth = width - paddingLeft - paddingRight
    const plotHeight = height - paddingTop - paddingBottom
    const times = series.flatMap(item => item.points.map(point => Date.parse(point.ts)))
    const updatedTime = Date.parse(updatedAt)
    const historyEnd = Math.max(Number.isFinite(updatedTime) ? updatedTime : times[times.length - 1], ...times)
    const historyStart = Math.max(historyEnd - days * 86400000, Math.min(...times))
    const historySpan = Math.max(historyEnd - historyStart, 60000)
    const visibleSpan = historySpan / zoom
    const maxTime = historyEnd - offset * (historySpan - visibleSpan)
    const minTime = maxTime - visibleSpan
    const visibleValues = series.flatMap(item => item.points
        .filter(point => Date.parse(point.ts) >= minTime && Date.parse(point.ts) <= maxTime)
        .map(point => point.equity))
    const values = visibleValues.length > 0 ? visibleValues : series.flatMap(item => item.points.map(point => point.equity))
    const rawMin = Math.min(...values)
    const rawMax = Math.max(...values)
    const span = rawMax - rawMin || Math.max(Math.abs(rawMax) * 0.02, 1)
    const center = (rawMin + rawMax) / 2
    const minValue = center - span * 0.55 / verticalZoom
    const maxValue = center + span * 0.55 / verticalZoom
    const x = (time: number) => paddingLeft + plotWidth * (time - minTime) / visibleSpan
    const y = (value: number) => paddingTop + plotHeight * (maxValue - value) / (maxValue - minValue)
    const buildLinePath = (points: EquityPoint[]) => points.map((point, index) =>
        `${index === 0 ? "M" : "L"}${x(Date.parse(point.ts)).toFixed(2)},${y(point.equity).toFixed(2)}`
    ).join(" ")
    const reset = () => { setZoom(1); setVerticalZoom(1); setOffset(0) }

    const comparable = series.map(item => item.label === "Общий баланс" ? { ...item, color: "#facc15" } : item)
    const totalSeries = comparable.filter(item => item.label === "Общий баланс")
    const platformSeries = comparable.filter(item => item.label !== "Общий баланс")
    const drawSeries = [...platformSeries, ...totalSeries]
    return (
        <div style={{ background: "var(--card)", borderRadius: 14, padding: 13 }}>
            <button type="button" onClick={() => setShowScale(!showScale)} style={{ border: "none", background: "transparent", color: "var(--text-muted)", fontSize: 11 }}>Масштаб</button>
            <div style={{ display: showScale ? "flex" : "none", flexWrap: "wrap", gap: 10, marginBottom: 10, fontSize: 12 }}>
                <label>Время ×{zoom.toFixed(1)} <input aria-label="Масштаб времени баланса" type="range" min="1" max="20" step="0.5" value={zoom} onChange={event => setZoom(Number(event.target.value))} /></label>
                <label>Баланс ×{verticalZoom.toFixed(1)} <input aria-label="Масштаб баланса" type="range" min="0.5" max="5" step="0.1" value={verticalZoom} onChange={event => setVerticalZoom(Number(event.target.value))} /></label>
                {zoom > 1 && <label>История <input aria-label="Сдвиг истории баланса" type="range" min="0" max="1" step="0.01" value={offset} onChange={event => setOffset(Number(event.target.value))} /></label>}
                <button onClick={reset} style={{ border: "none", borderRadius: 8, padding: "6px 10px", background: "var(--card-soft)", color: "var(--text)", cursor: "pointer" }}>Сбросить</button>
            </div>
            <div aria-label="Легенда балансов" style={{ display: "flex", flexDirection: "column", gap: 6, marginBottom: 8, fontSize: 11, color: "var(--text-dim)" }}>
                {totalSeries.map((item, index) => (
                    <span key={index} style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                        <span style={{ width: 10, height: 4, background: item.color }} />
                        {item.label}
                    </span>
                ))}
                <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
                    {platformSeries.map((item, index) => (
                        <span key={index} style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                            <span style={{ width: 10, height: 2, background: item.color }} />
                            {item.label}
                        </span>
                    ))}
                </div>
            </div>
            <svg
                viewBox={`0 0 ${width} ${height}`}
                preserveAspectRatio="none"
                role="img"
                aria-label="История стоимости портфеля"
                onWheel={event => {
                    if (event.ctrlKey) {
                        event.preventDefault()
                        setZoom(current => Math.max(1, Math.min(20, current + (event.deltaY < 0 ? 0.5 : -0.5))))
                    }
                }}
                style={{ width: "100%", height, display: "block", overflow: "hidden" }}
            >
                <defs>
                    <clipPath id={clipId}>
                        <rect x={paddingLeft} y={paddingTop} width={plotWidth} height={plotHeight} />
                    </clipPath>
                </defs>
                {[0, 1, 2, 3, 4].map(index => {
                    const value = maxValue - (maxValue - minValue) * index / 4
                    const lineY = y(value)
                    return (
                        <g key={index}>
                            <line x1={paddingLeft} y1={lineY} x2={width - paddingRight} y2={lineY} stroke="var(--border)" strokeDasharray="4 4" />
                            <text x={paddingLeft - 6} y={lineY + 3} textAnchor="end" fontSize="9" fill="var(--text-dim)">
                                {value.toLocaleString("ru-RU", { maximumFractionDigits: 2 })}
                            </text>
                        </g>
                    )
                })}
                <g clipPath={`url(#${clipId})`}>
                    {drawSeries.map((item, index) => (
                        <g key={index}>
                            <path d={buildLinePath(item.points)} fill="none" stroke={item.color} strokeWidth={item.label === "Общий баланс" ? "4" : "2"} vectorEffect="non-scaling-stroke" strokeLinejoin="round" strokeLinecap="round" />
                            {item.points.length === 1 && (
                                <circle cx={x(Date.parse(item.points[0].ts))} cy={y(item.points[0].equity)} r="3" fill={item.color} />
                            )}
                        </g>
                    ))}
                </g>
                <text x={paddingLeft} y={height - 6} fontSize="9" fill="var(--text-dim)">{formatUpdatedAt(new Date(minTime).toISOString())}</text>
                <text x={width - paddingRight} y={height - 6} textAnchor="end" fontSize="9" fill="var(--text-dim)">{formatUpdatedAt(new Date(maxTime).toISOString())}</text>
            </svg>
            {series.every(item => item.points.length === 1) && (
                <div style={{ marginTop: 8, fontSize: 11, color: "var(--text-dim)" }}>Пока доступна только текущая оценка. История появится по мере сохранения снимков.</div>
            )}
        </div>
    )
}


const seriesColors = [
    "#f59e0b",

    "#22c55e",

    "#8ab4f8",

    "#f28b82",
]


function currencySymbol(
    currency: string
): string {
    if (
        currency
        === "RUB"
    ) {
        return "₽"
    }

    return currency
}


type EquitySeries = {
    label: string

    points: EquityPoint[]

    color: string
}


function normalizePoints(points: EquityPoint[]): EquityPoint[] {
    return points
        .filter(point => Number.isFinite(Date.parse(point.ts)) && Number.isFinite(point.equity))
        .sort((left, right) => Date.parse(left.ts) - Date.parse(right.ts))
}


function buildSeries(
    history: DashboardHistory | null,
    platformColors: PlatformColors = defaultPlatformColors,
): EquitySeries[] {
    const byAccount = history?.points_by_account
        ? Object.fromEntries(Object.entries(history.points_by_account).map(([id, points]) => [id, normalizePoints(points)]))
        : null

    const historyAccounts = (
        history
        ?.accounts
        ?? []
    )

    if (
        byAccount
        !== null
        && historyAccounts.length
        > 0
    ) {
        const nameById = (
            new Map(
                historyAccounts.map(
                    account => [
                        account.id,

                        account.name,
                    ]
                )
            )
        )

        const mapped = (
            historyAccounts
            .filter(
                account => (
                    (
                        byAccount[
                            account.id
                        ]
                        ?? []
                    )
                    .length
                    > 0
                )
            )
            .map(
                (
                    account,
                    index,
                ) => ({
                    label: (
                        nameById.get(
                            account.id
                        )
                        ?? account.id
                    ),

                    points: (
                        byAccount[
                            account.id
                        ]
                    ),

                    color: platformColors[account.broker === "bybit" || account.name.toLowerCase().includes("bybit") ? "bybit" : "tinvest"],
                })
            )
        )

        if (
            mapped.length
            > 0
        ) {
            const totalPoints = normalizePoints(history?.total_points ?? [])
            if (totalPoints.length > 0) {
                const target = history?.total_balance_currency ?? "RUB"
                const converted = mapped.flatMap((item, index) => {
                    const account = historyAccounts.filter(value => (byAccount[value.id] ?? []).length > 0)[index]
                    const factor = account.currency === target ? 1 : target === "RUB" ? history?.exchange_rates_rub?.[account.currency] : undefined
                    return factor === undefined ? [] : [{ ...item, points: item.points.map(point => ({ ...point, equity: point.equity * factor })) }]
                })
                return [...converted, { label: "Общий баланс", points: totalPoints, color: "#facc15" }]
            }
            return mapped
        }
    }

    const byCurrency = history?.points_by_currency
        ? Object.fromEntries(Object.entries(history.points_by_currency).map(([currency, points]) => [currency, normalizePoints(points)]))
        : null

    if (
        byCurrency
        !== null
    ) {
        const mapped = (
            Object.entries(
                byCurrency
            )
            .filter(
                (
                    [
                        ,
                        seriesPoints,
                    ]
                ) => (
                    seriesPoints
                    .length
                    > 0
                )
            )
            .sort(
                (
                    [
                        a,
                    ],
                    [
                        b,
                    ]
                ) => (
                    a.localeCompare(
                        b
                    )
                )
            )
            .map(
                (
                    [
                        currency,
                        seriesPoints,
                    ],
                    index,
                ) => ({
                    label: (
                        currencySymbol(
                            currency
                        )
                    ),

                    points:
                    seriesPoints,

                    color: (
                        seriesColors[
                            index
                            % seriesColors
                            .length
                        ]
                    ),
                })
            )
        )

        if (
            mapped.length
            > 0
        ) {
            return mapped
        }
    }

    const points = normalizePoints(history?.points ?? [])

    if (
        points.length
        === 0
    ) {
        return []
    }

    return [
        {
            label:
            "₽",

            points,

            color: (
                seriesColors[
                    0
                ]
            ),
        },
    ]
}


function buildBalances(
    dashboard: Dashboard,
    history: DashboardHistory | null,
): Array<{
    currency: string
    value: number
}> {
    const accountBalances: Record<string, number> = {}

    for (const account of dashboard.accounts_detail ?? []) {
        if (account.balance === null) {
            continue
        }
        accountBalances[account.currency] = (
            (accountBalances[account.currency] ?? 0)
            + account.balance
        )
    }

    const historyByCurrency = {
        ...history?.equity_by_currency,
        ...accountBalances,
    }

    const availableByCurrency = (
        dashboard
        .available_cash_by_currency
        ?? {}
    )

    const investedByCurrency = (
        dashboard
        .invested_cash_by_currency
        ?? {}
    )

    const codes = (
        Array.from(
            new Set(
                [
                    ...Object.keys(
                        historyByCurrency
                        ?? {}
                    ),

                    ...Object.keys(
                        availableByCurrency
                    ),

                    ...Object.keys(
                        investedByCurrency
                    ),
                ]
            )
        ).sort()
    )

    return codes.map(
        (
            currency
        ) => ({
            currency,

            value: (
                historyByCurrency
               ?.[
                    currency
                ]
                ?? (
                    (
                        availableByCurrency[
                            currency
                        ]
                        ?? 0
                    )
                    + (
                        investedByCurrency[
                            currency
                        ]
                        ?? 0
                    )
                )
            ),
        })
    )
}


export function DashboardCard({
    dashboard,
}: Props) {
    const [platformColors, setPlatformColors] = useState(getStoredPlatformColors)

    useEffect(() => {
        const refreshColors = () => setPlatformColors(getStoredPlatformColors())
        window.addEventListener("storage", refreshColors)
        window.addEventListener("esm-platform-colors-changed", refreshColors)
        return () => {
            window.removeEventListener("storage", refreshColors)
            window.removeEventListener("esm-platform-colors-changed", refreshColors)
        }
    }, [])

    const [
        days,
        setDays,
    ] = useState(
        7
    )

    const [
        history,
        setHistory,
    ] = useState<
        DashboardHistory | null
    >(
        null
    )

    const [
        isHistoryLoading,
        setIsHistoryLoading,
    ] = useState(
        true
    )

    const [historyError, setHistoryError] = useState<string | null>(null)

    const [
        isAmountHidden,
        setIsAmountHidden,
    ] = useState(
        false
    )


    useEffect(
        () => {
            let cancelled = false
            let loading = false
            setHistory(null)
            setHistoryError(null)
            setIsHistoryLoading(true)

            async function load() {
                if (loading) {
                    return
                }
                loading = true

                try {
                    const data = (
                        await getDashboardHistory(
                            days
                        )
                    )

                    if (
                        !cancelled
                    ) {
                        setHistory(
                            data
                        )
                        setHistoryError(null)
                    }

                } catch (error) {
                    if (!cancelled) {
                        setHistoryError(error instanceof Error ? error.message : String(error))
                    }
                } finally {
                    loading = false
                    if (
                        !cancelled
                    ) {
                        setIsHistoryLoading(
                            false
                        )
                    }
                }
            }


            load()

            const timer = (
                setInterval(
                    load,

                    15000
                )
            )

            return () => {
                cancelled = true

                clearInterval(
                    timer
                )
            }
        },

        [
            days,
        ]
    )


    const equity =
        (
            dashboard
            .total_equity
        )
        ?? (
            (
                dashboard
                .available_cash
                ?? 0
            )
            + (
                dashboard
                .invested_cash
                ?? 0
            )
        )

    const balances = (
        buildBalances(
            dashboard,

            history,
        )
    )

    const pnlToday = (
        history
        ?.pnl_today
        ?? null
    )

    const pnlTodayPercent = (
        history
        ?.pnl_today_percent
        ?? null
    )

    const series = (
        buildSeries(
            history,
            platformColors,
        )
    )

    const hasChart = (
        series.length
        > 0
    )

    const pnlColor = (
        pnlToday
        === null
            ? "var(--text-dim)"
            : (
                pnlToday
                >= 0
                    ? "var(--profit)"
                    : "var(--loss)"
            )
    )

    return (
        <>
            <div
                style={{
                    marginBottom:
                    16,

                    color:
                    "var(--text)",
                }}
            >
                <div
                    style={{
                        display:
                        "flex",

                        alignItems:
                        "center",

                        gap:
                        8,

                        marginBottom:
                        6,
                    }}
                >
                    <span
                        style={{
                            fontSize:
                            14,

                            color:
                            "var(--text-muted)",
                        }}
                    >
                        Общие активы
                    </span>

                    <button
                        onClick={() => {
                            setIsAmountHidden(
                                !isAmountHidden
                            )
                        }}

                        style={{
                            background:
                            "transparent",

                            border:
                            "none",

                            padding:
                            0,

                            cursor:
                            "pointer",

                            fontSize:
                            14,

                            color:
                            "var(--text-dim)",
                        }}
                    >
                        {
                            isAmountHidden
                                ? "🚫"
                                : "👁"
                        }
                    </button>
                </div>

                <div style={{ marginBottom: 8 }}>
                    <div style={{ fontSize: 13, color: "var(--text-muted)" }}>Общий баланс</div>
                    <b style={{ fontSize: 36 }}>{isAmountHidden ? "•••••" : dashboard.total_balance == null ? "—" : formatEquity(dashboard.total_balance)} {currencySymbol(dashboard.total_balance_currency ?? "RUB")}</b>
                    {dashboard.balance_conversion_note && <div role="status" style={{ fontSize: 12 }}>{dashboard.balance_conversion_note}</div>}
                </div>
                <div style={{ display: balances.length > 1 ? "flex" : "none", alignItems: "baseline", gap: 12, marginBottom: 4, overflowX: "auto" }}>

                    {
                        balances.length
                        > 1
                            ? balances.map(
                                (
                                    balance,
                                    index,
                                ) => (
                                    <div
                                        key={
                                            balance
                                            .currency
                                        }

                                        style={{
                                            display:
                                            "flex",

                                            alignItems:
                                            "baseline",

                                            gap:
                                            index
                                            === 0
                                                ? 8
                                                : 6,

                                            marginRight:
                                            index
                                            === (
                                                balances
                                                .length
                                                - 1
                                            )
                                                ? 0
                                                : 18,
                                        }}
                                    >
                                        <span
                                            style={{
                                                fontSize:
                                                18,

                                                fontWeight:
                                                700,

                                                letterSpacing:
                                                "-0.5px",
                                            }}
                                        >
                                            {
                                                isAmountHidden
                                                    ? "•••••"
                                                    : formatEquity(
                                                        balance
                                                        .value
                                                    )
                                            }
                                        </span>

                                        <span
                                            style={{
                                                fontSize:
                                                13,

                                                color:
                                                "var(--text-muted)",
                                            }}
                                        >
                                            {
                                                currencySymbol(
                                                    balance
                                                    .currency
                                                )
                                            }
                                        </span>
                                    </div>
                                )
                            )
                            : (
                                <>
                                    <span
                                        style={{
                                            fontSize:
                                            40,

                                            fontWeight:
                                            700,

                                            letterSpacing:
                                            "-0.5px",
                                        }}
                                    >
                                        {
                                            isAmountHidden
                                                ? "•••••"
                                                : formatEquity(
                                                    equity
                                                )
                                        }
                                    </span>

                                    <span
                                        style={{
                                            fontSize:
                                            18,

                                            color:
                                            "var(--text-muted)",
                                        }}
                                    >
                                        ₽
                                    </span>
                                </>
                            )
                    }
                </div>

                <div
                    style={{
                        display:
                        "flex",

                        alignItems:
                        "baseline",

                        gap:
                        6,

                        marginBottom:
                        8,
                    }}
                >
                    <span
                        style={{
                            fontSize:
                            13,

                            color:
                            "var(--text-muted)",
                        }}
                    >
                        P&L за сегодня
                    </span>

                    <b
                        style={{
                            fontSize:
                            14,

                            color:
                            pnlColor,
                        }}
                    >
                        {
                            pnlToday
                            === null
                                ? "—"
                                : `${
                                    formatSigned(
                                        pnlToday
                                    )
                                } ₽${
                                    pnlTodayPercent
                                    === null
                                        ? ""
                                        : ` (${
                                            formatSignedPercent(
                                                pnlTodayPercent
                                            )
                                        })`
                                }`
                        }
                    </b>
                </div>


                {hasChart ? (
                    <EquityChart
                        key={days}
                        series={
                            series
                        }
                        days={days}
                        updatedAt={history?.updated_at ?? new Date().toISOString()}
                    />
                ) : (
                    <div
                        style={{
                            height:
                            220,

                            display:
                            "flex",

                            alignItems:
                            "center",

                            justifyContent:
                            "center",

                            fontSize:
                            13,

                            color:
                            "var(--text-dim)",

                            borderRadius:
                            12,

                            background:
                            "var(--bg-soft)",
                        }}
                    >
                        {
                            isHistoryLoading
                                ? "Загрузка графика..."
                                : historyError ? "История недоступна" : "Нет сохранённых снимков баланса"
                        }
                    </div>
                )}

                <div
                    style={{
                        display:
                        "flex",

                        gap:
                        6,

                        marginTop:
                        10,
                    }}
                >
                    {periodOptions.map(
                        (
                            option
                        ) => (
                            <button
                                key={
                                    option.days
                                }

                                onClick={() => {
                                    setDays(
                                        option.days
                                    )
                                }}

                                style={{
                                    padding:
                                    "6px 12px",

                                    borderRadius:
                                    8,

                                    border:
                                    "none",

                                    background:
                                    days
                                    === option.days
                                        ? "var(--card-soft)"
                                        : "transparent",

                                    color:
                                    days
                                    === option.days
                                        ? "var(--text)"
                                        : "var(--text-dim)",

                                    fontWeight:
                                    days
                                    === option.days
                                        ? 600
                                        : 400,

                                    cursor:
                                    days
                                    === option.days
                                        ? "default"
                                        : "pointer",
                                }}
                            >
                                {
                                    option.label
                                }
                            </button>
                        )
                    )}
                </div>

                {historyError && (
                    <div role="alert" style={{ marginTop: 8, fontSize: 12, color: "var(--loss)" }}>Не удалось обновить историю: {historyError}</div>
                )}

                {history?.history_note && (
                    <div style={{ marginTop: 8, fontSize: 11, color: "var(--text-dim)" }}>
                        {history.history_note}
                    </div>
                )}

                <div
                    style={{
                        marginTop:
                        8,

                        fontSize:
                        11,

                        color:
                        "var(--text-dim)",
                    }}
                >
                    Последнее обновление: {
                        history
                            ? formatUpdatedAt(
                                history.updated_at
                            )
                            : "—"
                    }
                </div>
            </div>
        </>
    )
}
