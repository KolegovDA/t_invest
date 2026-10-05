import {
    useEffect,
    useState,
} from "react"

import {
    getSessionChart,
} from "../api"

import type {
    SessionChartResponse,
} from "../types"


const WIDTH = 640
const HEIGHT = 480
const TRAILING_COLOR = "#a78bfa"
const PADDING_LEFT = 8
const PADDING_RIGHT = 8
const PADDING_TOP = 12
const PADDING_BOTTOM = 22


const INTERVAL_OPTIONS: {
    value: string
    label: string
}[] = [
        {
            value: "15m",
            label: "15м",
        },
        {
            value: "1h",
            label: "1ч",
        },
        {
            value: "4h",
            label: "4ч",
        },
        {
            value: "1d",
            label: "1д",
        },
    ]


const PLANNED_LEVEL_STATUSES = (
    [
        "WAITING_PRICE",

        "WAITING_FOR_FUNDS",

        "TRAILING_ENTRY",
    ]
)


export function SessionChartCard({
    ticker,
}: {
    ticker: string
}) {
    const [
        chart,
        setChart,
    ] = useState<
        SessionChartResponse
        | null
    >(null)

    const [
        interval,
        setIntervalValue,
    ] = useState(
        "15m"
    )
    const [zoom, setZoom] = useState(1)
    const [verticalZoom, setVerticalZoom] = useState(1)
    const [offset, setOffset] = useState(0)

    const [
        isLoading,
        setIsLoading,
    ] = useState(
        true
    )

    const [
        error,
        setError,
    ] = useState<
        string | null
    >(null)


    useEffect(
        () => {
            let cancelled =
                false

            setIsLoading(
                true
            )

            setError(
                null
            )

            function loadChart() {
                getSessionChart(
                    ticker,
                    interval === "15m" ? 7 : interval === "1h" ? 30 : 90,
                    interval
                )
                .then(
                    data => {
                        if (
                            cancelled
                        ) {
                            return
                        }

                        setChart(
                            data
                        )
                    }
                )
                .catch(
                    currentError => {
                        if (
                            cancelled
                        ) {
                            return
                        }

                        setError(
                            currentError
                            instanceof Error
                                ? currentError.message
                                : String(
                                    currentError
                                )
                        )
                    }
                )
                .finally(
                    () => {
                        if (
                            cancelled
                        ) {
                            return
                        }

                        setIsLoading(
                            false
                        )
                    }
                )
            }
            loadChart()
            const timer = window.setInterval(loadChart, 15000)

            return () => {
                cancelled = true
                window.clearInterval(timer)
            }
        },

        [
            ticker,

            interval,
        ]
    )


    const intervalButtons = (
        <div style={{ display: "flex", gap: 6, marginBottom: 12, flexWrap: "wrap" }}>
            {INTERVAL_OPTIONS.map(option => (
                <button
                    key={option.value}
                    onClick={() => {
                        setIntervalValue(option.value)
                        setZoom(1)
                        setVerticalZoom(1)
                        setOffset(0)
                    }}
                    aria-pressed={interval === option.value}
                    style={{
                        border: "none",
                        borderRadius: 8,
                        padding: "8px 12px",
                        color: "var(--text)",
                        background: interval === option.value ? "var(--accent-soft)" : "var(--card-soft)",
                        cursor: "pointer",
                    }}
                >
                    {option.label}
                </button>
            ))}
        </div>
    )

    if (
        isLoading
    ) {
        return (
            <div
                style={{
                    background: "var(--card)",

                    borderRadius:
                    14,

                    padding:
                    13,

                    marginTop:
                    10,

                    color:
                    "var(--text-muted)",

                    fontSize:
                    13,
                }}
            >
                {intervalButtons}
                <div style={{ height: 280 }}>График загружается...</div>
            </div>
        )
    }

    if (
        error
    ) {
        return (
            <div
                style={{
                    background: "var(--card)",

                    borderRadius:
                    14,

                    padding:
                    13,

                    marginTop:
                    10,

                    color:
                    "var(--loss)",

                    fontSize:
                    13,
                }}
            >
                {intervalButtons}
                График недоступен: {
                    error
                }
            </div>
        )
    }

    const candles = [...(chart?.candles ?? [])]
        .filter(candle => Number.isFinite(new Date(candle.time).getTime())
            && [candle.open, candle.high, candle.low, candle.close].every(value => Number.isFinite(Number(value))))
        .sort((left, right) => new Date(left.time).getTime() - new Date(right.time).getTime())

    const levels = (
        chart?.levels
        ?? []
    )

    const positions = (
        chart?.positions
        ?? []
    )

    const trades = (
        chart?.trades
        ?? []
    )

    if (
        candles.length
        < 2
    ) {
        return (
            <div
                style={{
                    background: "var(--card)",

                    borderRadius:
                    14,

                    padding:
                    13,

                    marginTop:
                    10,

                    color:
                    "var(--text-muted)",

                    fontSize:
                    13,
                }}
            >
                {intervalButtons}
                Нет данных свечей для графика
                {
                    " "
                }
                {
                    ticker
                }
                .
            </div>
        )
    }

    const closes = (
        candles.map(
            candle =>
                Number(
                    candle.close
                )
        )
    )

    const buyPrices = (
        trades
        .filter(
            trade => (
                trade.side
                === "BUY"
            )
        )
        .map(
            trade =>
                Number(
                    trade.price
                )
        )
    )

    const sellPrices = (
        trades
        .filter(
            trade => (
                trade.side
                === "SELL"
            )
        )
        .map(
            trade =>
                Number(
                    trade.price
                )
        )
    )

    const avgBuy = (
        buyPrices.length
        > 0
            ? (
                buyPrices
                .reduce(
                    (
                        sum,
                        value
                    ) => (
                        sum
                        + value
                    ),

                    0
                )
                / buyPrices.length
            )
            : null
    )

    const avgSell = (
        sellPrices.length
        > 0
            ? (
                sellPrices
                .reduce(
                    (
                        sum,
                        value
                    ) => (
                        sum
                        + value
                    ),

                    0
                )
                / sellPrices.length
            )
            : null
    )

    const plannedLevels = (
        levels
        .filter(
            level => (
                PLANNED_LEVEL_STATUSES
                .includes(
                    level.status
                )
            )
        )
    )

    const candleValues = candles.flatMap(candle => [
        Number(candle.low),
        Number(candle.high),
        Number(candle.close),
    ]).filter(Number.isFinite)
    const allValues = candleValues.length > 0 ? candleValues : closes

    const rawMin = (
        Math
        .min(
            ...allValues
        )
    )

    const rawMax = (
        Math
        .max(
            ...allValues
        )
    )

    const span = (
        rawMax
        - rawMin
        || 1
    )

    const centerValue = (rawMin + rawMax) / 2
    const minValue = centerValue - span * 0.55 / verticalZoom
    const maxValue = centerValue + span * 0.55 / verticalZoom

    const plotHeight = (
        HEIGHT
        - PADDING_TOP
        - PADDING_BOTTOM
    )

    const plotWidth = (
        WIDTH
        - PADDING_LEFT
        - PADDING_RIGHT
    )


    function y(
        value: number
    ): number {
        return (
            PADDING_TOP
            + plotHeight
            * (
                1
                - (
                    value
                    - minValue
                )
                / (
                    maxValue
                    - minValue
                )
            )
        )
    }


    const times = (
        candles.map(
            candle =>
                new Date(
                    candle.time
                )
                .getTime()
        )
    )

    const historyEnd = times[times.length - 1]
    const startedAt = chart?.started_at ? Date.parse(chart.started_at) : NaN
    const historyStart = Number.isFinite(startedAt) ? startedAt : times[0]
    const historySpan = Math.max(historyEnd - historyStart, 1)
    const visibleSpan = historySpan / zoom
    const maxTime = historyEnd - offset * (historySpan - visibleSpan)
    const minTime = maxTime - visibleSpan


    function xByTime(
        time: number
    ): number {
        if (
            maxTime
            === minTime
        ) {
            return (
                PADDING_LEFT
                + plotWidth
                / 2
            )
        }

        const ratio = (
            (
                time
                - minTime
            )
            / (
                maxTime
                - minTime
            )
        )

        return (
            PADDING_LEFT
            + plotWidth
            * ratio
        )
    }


    const closePath = (
        closes
        .map(
            (
                close,
                index,
            ) => (
                `${index === 0 ? "M" : "L"}`
                + xByTime(
                    times[
                        index
                    ]
                )
                .toFixed(
                    1
                )
                + ","
                + y(
                    close
                )
                .toFixed(
                    1
                )
            )
        )
        .join(
            " "
        )
    )

    const firstDate = (
        new Date(
            minTime
        )
    )

    const lastDate = (
        new Date(
            times[
                times.length
                - 1
            ]
        )
    )


    return (
        <div
            style={{
                background: "var(--card)",

                borderRadius:
                14,

                padding:
                13,

                marginTop:
                10,
            }}
        >
            <div
                style={{
                    display:
                    "flex",

                    justifyContent:
                    "space-between",

                    alignItems:
                    "center",

                    gap:
                    8,

                    flexWrap:
                    "wrap",

                    marginBottom:
                    8,
                }}
            >
                <h3
                    style={{
                        marginTop:
                        0,

                        marginBottom:
                        0,
                    }}
                >
                    График {
                        ticker
                    }
                    {" — уровни, входы, траллы"}
                </h3>

                <div
                    style={{
                        display:
                        "flex",

                        gap:
                        4,
                    }}
                >
                    {
                        INTERVAL_OPTIONS
                        .map(
                            option => (
                                <button
                                    key={
                                        option.value
                                    }

                                    onClick={() => {
                                        setIntervalValue(
                                            option.value
                                        )
                                    }}

                                    style={{
                                        border:
                                        "none",

                                        background: (
                                            interval
                                            === option.value
                                                ? "var(--accent-soft)"
                                                : "var(--card-soft)"
                                        ),

                                        color:
                                        "var(--text)",

                                        borderRadius:
                                        6,

                                        padding:
                                        "4px 8px",

                                        fontSize:
                                        11,

                                        fontWeight:
                                        interval
                                        === option.value
                                            ? 700
                                            : 500,

                                        cursor:
                                        "pointer",
                                    }}
                                >
                                    {
                                        option.label
                                    }
                                </button>
                            )
                        )
                    }
                </div>
            </div>

            <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginBottom: 10, fontSize: 12 }}>
                <label>Время ×{zoom.toFixed(1)} <input aria-label="Масштаб времени" type="range" min="1" max="20" step="0.5" value={zoom} onChange={event => setZoom(Number(event.target.value))} /></label>
                <label>Цена ×{verticalZoom.toFixed(1)} <input aria-label="Масштаб цены" type="range" min="0.5" max="5" step="0.1" value={verticalZoom} onChange={event => setVerticalZoom(Number(event.target.value))} /></label>
                {zoom > 1 && <label>История <input aria-label="Сдвиг временного окна" type="range" min="0" max="1" step="0.01" value={offset} onChange={event => setOffset(Number(event.target.value))} /></label>}
                <button onClick={() => { setZoom(1); setVerticalZoom(1); setOffset(0) }} style={{ border: "none", borderRadius: 8, padding: "6px 10px", background: "var(--card-soft)", color: "var(--text)", cursor: "pointer" }}>Сбросить</button>
            </div>
            <svg
                viewBox=
                    {`0 0 ${WIDTH} ${HEIGHT}`}

                preserveAspectRatio="none"
                onWheel={event => {
                    if (event.ctrlKey) {
                        event.preventDefault()
                        setZoom(current => Math.max(1, Math.min(20, current + (event.deltaY < 0 ? 0.5 : -0.5))))
                    }
                }}
                style={{ width: "100%", height: 480, display: "block", overflow: "hidden" }}
            >
                {levels.map(
                    level => {
                        const value = (
                            Number(
                                level.price
                            )
                        )

                        if (
                            value
                            < minValue
                            || value
                            > maxValue
                        ) {
                            return null
                        }

                        const lineY = (
                            y(
                                value
                            )
                        )

                        return (
                            <g
                                key={
                                    "level-"
                                    + level.level_index
                                }
                            >
                                <line
                                    x1={
                                        PADDING_LEFT
                                    }

                                    y1={
                                        lineY
                                    }

                                    x2={
                                        WIDTH
                                        - PADDING_RIGHT
                                    }

                                    y2={
                                        lineY
                                    }

                                    stroke=
                                        "var(--border)"

                                    strokeDasharray=
                                        "4 4"

                                    strokeWidth=
                                        "1"
                                />

                                <text
                                    x={
                                        WIDTH
                                        - PADDING_RIGHT
                                    }

                                    y={
                                        lineY
                                        - 3
                                    }

                                    textAnchor=
                                        "end"

                                    fontSize=
                                        "9"

                                    fill=
                                        "var(--text-dim)"
                                >
                                    ур.{
                                        level.level_index
                                    }
                                    {" "}
                                    {
                                        level
                                            .status
                                    }
                                </text>
                            </g>
                        )
                    }
                )}

                {positions.map(
                    (
                        position,
                        index,
                    ) => {
                        const entry = (
                            Number(
                                position.entry_price
                            )
                        )

                        const entryY = (
                            y(
                                entry
                            )
                        )

                        const trailingTarget = (
                            position.trailing_exit_target_price
                        )

                        const trailingValue = (
                            trailingTarget
                            === null
                                ? null
                                : Number(
                                    trailingTarget
                                )
                        )

                        return (
                            <g
                                key={
                                    "pos-"
                                    + position.level_index
                                    + "-"
                                    + index
                                }
                            >
                                <line
                                    x1={
                                        PADDING_LEFT
                                    }

                                    y1={
                                        entryY
                                    }

                                    x2={
                                        PADDING_LEFT
                                        + plotWidth
                                        * 0.25
                                    }

                                    y2={
                                        entryY
                                    }

                                    stroke=
                                        "var(--profit)"

                                    strokeWidth=
                                        "2"
                                />

                                <text
                                    x={
                                        PADDING_LEFT
                                    }

                                    y={
                                        entryY
                                        - 3
                                    }

                                    fontSize=
                                        "9"

                                    fill=
                                        "var(--profit)"
                                >
                                    вход #{
                                        position.level_index
                                    }
                                    {" ×"}
                                    {
                                        position.quantity
                                    }
                                </text>

                                {
                                    trailingValue
                                    !== null
                                    && trailingValue
                                    >= minValue
                                    && trailingValue
                                    <= maxValue
                                    && (
                                        <>
                                            <line
                                                x1={
                                                    PADDING_LEFT
                                                    + plotWidth
                                                    * 0.3
                                                }

                                                y1={
                                                    y(
                                                        trailingValue
                                                    )
                                                }

                                                x2={
                                                    WIDTH
                                                    - PADDING_RIGHT
                                                }

                                                y2={
                                                    y(
                                                        trailingValue
                                                    )
                                                }

                                                stroke={TRAILING_COLOR}

                                                strokeDasharray=
                                                    "6 3"

                                                strokeWidth=
                                                    "1.5"
                                            />

                                            <text
                                                x={
                                                    WIDTH
                                                    - PADDING_RIGHT
                                                }

                                                y={
                                                    y(
                                                        trailingValue
                                                    )
                                                    - 3
                                                }

                                                textAnchor=
                                                    "end"

                                                fontSize=
                                                    "9"

                                                fill={TRAILING_COLOR}
                                            >
                                                тралл #{
                                                    position.level_index
                                                }
                                            </text>
                                        </>
                                    )
                                }
                            </g>
                        )
                    }
                )}

                <path
                    d={
                        closePath
                    }

                    fill=
                        "none"

                    stroke=
                        "var(--accent)"

                    strokeWidth=
                        "2"
                />

                {avgBuy
                !== null
                && avgBuy
                >= minValue
                && avgBuy
                <= maxValue
                && (
                    <g
                        key="avg-buy"
                    >
                        <line
                            x1={
                                PADDING_LEFT
                            }

                            y1={
                                y(
                                    avgBuy
                                )
                            }

                            x2={
                                WIDTH
                                - PADDING_RIGHT
                            }

                            y2={
                                y(
                                    avgBuy
                                )
                            }

                            stroke=
                                "var(--profit)"

                            strokeDasharray=
                                "2 3"

                            strokeWidth=
                                "1.5"
                        />

                        <text
                            x={
                                PADDING_LEFT
                                + 2
                            }

                            y={
                                y(
                                    avgBuy
                                )
                                - 3
                            }

                            fontSize=
                                "9"

                            fill=
                                "var(--profit)"
                        >
                            Avg.Buy {
                                avgBuy
                                .toFixed(
                                    2
                                )
                            }
                        </text>
                    </g>
                )}

                {avgSell
                !== null
                && avgSell
                >= minValue
                && avgSell
                <= maxValue
                && (
                    <g
                        key="avg-sell"
                    >
                        <line
                            x1={
                                PADDING_LEFT
                            }

                            y1={
                                y(
                                    avgSell
                                )
                            }

                            x2={
                                WIDTH
                                - PADDING_RIGHT
                            }

                            y2={
                                y(
                                    avgSell
                                )
                            }

                            stroke=
                                "var(--loss)"

                            strokeDasharray=
                                "2 3"

                            strokeWidth=
                                "1.5"
                        />

                        <text
                            x={
                                PADDING_LEFT
                                + 2
                            }

                            y={
                                y(
                                    avgSell
                                )
                                + 10
                            }

                            fontSize=
                                "9"

                            fill=
                                "var(--loss)"
                        >
                            Avg.Sell {
                                avgSell
                                .toFixed(
                                    2
                                )
                            }
                        </text>
                    </g>
                )}

                {plannedLevels.map(
                    level => {
                        const value = (
                            Number(
                                level.price
                            )
                        )

                        if (
                            value
                            < minValue
                            || value
                            > maxValue
                        ) {
                            return null
                        }

                        return (
                            <circle
                                key={
                                    "plan-"
                                    + level.level_index
                                }

                                cx={
                                    WIDTH
                                    - PADDING_RIGHT
                                    - 5
                                }

                                cy={
                                    y(
                                        value
                                    )
                                }

                                r=
                                    "3"

                                fill=
                                    "none"

                                stroke=
                                    "var(--accent)"

                                strokeWidth=
                                    "1.5"
                            />
                        )
                    }
                )}

                {trades.map(
                    (
                        trade,
                        index,
                    ) => {
                        const time = (
                            new Date(
                                trade.time
                            )
                            .getTime()
                        )

                        if (
                            time
                            < minTime
                            || time
                            > maxTime
                        ) {
                            return null
                        }

                        const cx = (
                            xByTime(
                                time
                            )
                        )

                        const cy = (
                            y(
                                Number(
                                    trade.price
                                )
                            )
                        )

                        const isBuy = (
                            trade.side
                            === "BUY"
                        )

                        const isTrailing = (
                            trade.side
                            === "TRAILING"
                        )

                        if (
                            isTrailing
                        ) {
                            return (
                                <circle
                                    key={
                                        "trade-"
                                        + index
                                    }

                                    cx={
                                        cx
                                    }

                                    cy={
                                        cy
                                    }

                                    r=
                                        "2.5"

                                    fill={TRAILING_COLOR}
                                />
                            )
                        }

                        return (
                            <circle
                                key={
                                    "trade-"
                                    + index
                                }

                                cx={
                                    cx
                                }

                                cy={
                                    cy
                                }

                                r=
                                    "4"

                                fill={
                                    isBuy
                                        ? "var(--profit)"
                                        : "var(--loss)"
                                }

                                stroke=
                                    "white"

                                strokeWidth=
                                    "1"
                            />
                        )
                    }
                )}

                <text
                    x={
                        PADDING_LEFT
                    }

                    y={
                        HEIGHT
                        - 6
                    }

                    fontSize=
                        "9"

                    fill=
                        "var(--text-dim)"
                >
                    {
                        firstDate
                        .toLocaleDateString(
                            "ru-RU"
                        )
                    }
                </text>

                <text
                    x={
                        WIDTH
                        - PADDING_RIGHT
                    }

                    y={
                        HEIGHT
                        - 6
                    }

                    textAnchor=
                        "end"

                    fontSize=
                        "9"

                    fill=
                        "var(--text-dim)"
                >
                    {
                        lastDate
                        .toLocaleDateString(
                            "ru-RU"
                        )
                    }
                </text>

                <text
                    x={
                        PADDING_LEFT
                    }

                    y={
                        PADDING_TOP
                        + 8
                    }

                    fontSize=
                        "9"

                    fill=
                        "var(--text-dim)"
                >
                    {
                        maxValue
                        .toFixed(
                            2
                        )
                    }
                </text>

                <text
                    x={
                        PADDING_LEFT
                    }

                    y={
                        PADDING_TOP
                        + plotHeight
                    }

                    fontSize=
                        "9"

                    fill=
                        "var(--text-dim)"
                >
                    {
                        minValue
                        .toFixed(
                            2
                        )
                    }
                </text>
            </svg>

            <div
                style={{
                    display:
                    "flex",

                    gap:
                    14,

                    flexWrap:
                    "wrap",

                    marginTop:
                    6,

                    fontSize:
                    11,

                    color:
                    "var(--text-muted)",
                }}
            >
                <span>
                    <b
                        style={{
                            color:
                            "var(--accent)",
                        }}
                    >
                        ─
                    </b>
                    {" цена закрытия свечи"}
                </span>

                <span>
                    <b
                        style={{
                            color:
                            "var(--border)",
                        }}
                    >
                        ┅
                    </b>
                    {" уровни сетки"}
                </span>

                <span>
                    <b
                        style={{
                            color:
                            "var(--profit)",
                        }}
                    >
                        ─
                    </b>
                    {" входы"}
                </span>

                <span>
                    <b
                        style={{
                            color:
                            TRAILING_COLOR,
                        }}
                    >
                        ┅
                    </b>
                    {" траллы (текущие)"}
                </span>

                <span>
                    <b
                        style={{
                            color:
                            TRAILING_COLOR,
                        }}
                    >
                        •
                    </b>
                    {" траллы (история)"}
                </span>

                <span>
                    <b
                        style={{
                            color:
                            "var(--profit)",
                        }}
                    >
                        ●
                    </b>
                    {" покупка"}

                    {"  "}

                    <b
                        style={{
                            color:
                            "var(--loss)",
                        }}
                    >
                        ●
                    </b>
                    {" продажа"}
                </span>

                <span>
                    <b
                        style={{
                            color:
                            "var(--profit)",
                        }}
                    >
                        ┄
                    </b>
                    {" Avg.Buy / Avg.Sell"}
                </span>

                <span>
                    <b
                        style={{
                            color:
                            "var(--accent)",
                        }}
                    >
                        ○
                    </b>
                    {" плановые точки"}
                </span>
            </div>
        </div>
    )
}
