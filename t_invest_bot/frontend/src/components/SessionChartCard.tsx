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
const HEIGHT = 280
const PADDING_LEFT = 8
const PADDING_RIGHT = 8
const PADDING_TOP = 12
const PADDING_BOTTOM = 22


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

            getSessionChart(
                ticker,
                90
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

            return () => {
                cancelled = true
            }
        },

        [
            ticker,
        ]
    )


    if (
        isLoading
    ) {
        return (
            <div
                style={{
                    background:
                    "white",

                    borderRadius:
                    14,

                    padding:
                    13,

                    marginTop:
                    10,

                    color:
                    "#6b7280",

                    fontSize:
                    13,
                }}
            >
                График загружается...
            </div>
        )
    }

    if (
        error
    ) {
        return (
            <div
                style={{
                    background:
                    "white",

                    borderRadius:
                    14,

                    padding:
                    13,

                    marginTop:
                    10,

                    color:
                    "#b91c1c",

                    fontSize:
                    13,
                }}
            >
                График недоступен: {
                    error
                }
            </div>
        )
    }

    const candles = (
        chart?.candles
        ?? []
    )

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
                    background:
                    "white",

                    borderRadius:
                    14,

                    padding:
                    13,

                    marginTop:
                    10,

                    color:
                    "#6b7280",

                    fontSize:
                    13,
                }}
            >
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

    const levelPrices = (
        levels.map(
            level =>
                Number(
                    level.price
                )
        )
    )

    const entryPrices = (
        positions.map(
            position =>
                Number(
                    position.entry_price
                )
        )
    )

    const tradePrices = (
        trades.map(
            trade =>
                Number(
                    trade.price
                )
        )
    )

    const allValues = [
        ...closes,
        ...levelPrices,
        ...entryPrices,
        ...tradePrices,
    ]

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

    const minValue = (
        rawMin
        - span
        * 0.05
    )

    const maxValue = (
        rawMax
        + span
        * 0.05
    )

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

    const minTime = (
        times[
            0
        ]
    )

    const maxTime = (
        times[
            times.length
            - 1
        ]
    )


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
            times[0]
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
                background:
                "white",

                borderRadius:
                14,

                padding:
                13,

                marginTop:
                10,
            }}
        >
            <h3
                style={{
                    marginTop:
                    0,

                    marginBottom:
                    8,
                }}
            >
                График {
                    ticker
                }
                {" — уровни, входы, траллы"}
            </h3>

            <svg
                viewBox=
                    {`0 0 ${WIDTH} ${HEIGHT}`}

                style={{
                    width:
                    "100%",

                    height:
                    "auto",

                    display:
                    "block",
                }}
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
                                        "#d1d5db"

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
                                        "#9ca3af"
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
                                        "#15803d"

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
                                        "#15803d"
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

                                                stroke=
                                                    "#ea580c"

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

                                                fill=
                                                    "#ea580c"
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
                        "#2563eb"

                    strokeWidth=
                        "2"
                />

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

                                    fill=
                                        "#ea580c"
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
                                        ? "#15803d"
                                        : "#b91c1c"
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
                        "#9ca3af"
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
                        "#9ca3af"
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
                        "#9ca3af"
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
                        "#9ca3af"
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
                    "#6b7280",
                }}
            >
                <span>
                    <b
                        style={{
                            color:
                            "#2563eb",
                        }}
                    >
                        ─
                    </b>
                    {" цена закрытия дня"}
                </span>

                <span>
                    <b
                        style={{
                            color:
                            "#d1d5db",
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
                            "#15803d",
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
                            "#ea580c",
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
                            "#ea580c",
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
                            "#15803d",
                        }}
                    >
                        ●
                    </b>
                    {" покупка"}

                    {"  "}

                    <b
                        style={{
                            color:
                            "#b91c1c",
                        }}
                    >
                        ●
                    </b>
                    {" продажа"}
                </span>
            </div>
        </div>
    )
}
