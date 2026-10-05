import {
    useCallback,
    useEffect,
    useState,
} from "react"

import {
    addMoneyMovement,
    getMoneyMovements,
} from "./api"

import type {
    MoneyMovement,
    MoneyMovementsResponse,
} from "./types"


function formatMoney(
    value: string | null
): string {
    if (
        value === null
    ) {
        return "—"
    }

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
                maximumFractionDigits: 2,
            }
        )
        + " ₽"
    )
}


function formatPercent(
    value: string | null
): string {
    if (
        value === null
    ) {
        return "—"
    }

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
                maximumFractionDigits: 2,
            }
        )
        + "%"
    )
}


function formatTime(
    createdAt: string
): string {
    const date =
        new Date(
            createdAt
        )

    if (
        Number.isNaN(
            date.getTime()
        )
    ) {
        return createdAt
    }

    return (
        date.toLocaleString(
            "ru-RU",
            {
                day: "2-digit",
                month: "2-digit",
                year: "2-digit",
                hour: "2-digit",
                minute: "2-digit",
            }
        )
    )
}


export function AccountMovementsCard({
    accountId,
}: {
    accountId: string
}) {
    const [
        movements,
        setMovements,
    ] = useState<
        MoneyMovement[]
    >([])

    const [
        performance,
        setPerformance,
    ] = useState<
        MoneyMovementsResponse[
            "performance"
        ]
        | null
    >(null)

    const [
        amount,
        setAmount,
    ] = useState(
        ""
    )

    const [
        note,
        setNote,
    ] = useState(
        ""
    )

    const [
        isExpanded,
        setIsExpanded,
    ] = useState(
        false
    )

    const [
        isSaving,
        setIsSaving,
    ] = useState(
        false
    )

    const [
        error,
        setError,
    ] = useState<
        string | null
    >(null)


    const applyResponse = (
        useCallback(
            (
                data: MoneyMovementsResponse
            ) => {
                setMovements(
                    data.movements
                )

                setPerformance(
                    data.performance
                )
            },
            []
        )
    )


    useEffect(
        () => {
            if (
                !isExpanded
            ) {
                return
            }

            let cancelled =
                false

            getMoneyMovements(
                accountId
            )
                .then(
                    data => {
                        if (
                            cancelled
                        ) {
                            return
                        }

                        applyResponse(
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

            return () => {
                cancelled = true
            }
        },

        [
            accountId,
            isExpanded,
            applyResponse,
        ]
    )


    function saveMovement(
        sign: 1 | -1
    ) {
        const numeric =
            Number(
                amount.replace(
                    ",",
                    "."
                )
            )

        if (
            Number.isNaN(
                numeric
            )
            || numeric
            <= 0
        ) {
            setError(
                "Введите положительную сумму"
            )

            return
        }

        setIsSaving(
            true
        )

        setError(
            null
        )

        addMoneyMovement(
            accountId,

            (
                numeric
                * sign
            ).toFixed(
                2
            ),

            note
        )
            .then(
                data => {
                    applyResponse(
                        data
                    )

                    setAmount(
                        ""
                    )

                    setNote(
                        ""
                    )
                }
            )
            .catch(
                currentError => {
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
                    setIsSaving(
                        false
                    )
                }
            )
    }


    return (
        <div
            style={{
                marginTop:
                16,

                borderTop:
                "1px solid var(--border)",

                paddingTop:
                12,
            }}
        >
            <button
                type="button"

                onClick={() => {
                    setIsExpanded(
                        current => (
                            !current
                        )
                    )
                }}

                style={{
                    background:
                    "none",

                    border:
                    "none",

                    padding:
                    0,

                    cursor:
                    "pointer",

                    fontWeight:
                    700,

                    color:
                    "var(--accent)",
                }}
            >
                {
                    isExpanded
                        ? "▼ Пополнения и выводы"
                        : "▶ Пополнения и выводы"
                }
            </button>

            {isExpanded && (
                <>
                    {performance && (
                        <div
                            style={{
                                marginTop:
                                12,

                                display:
                                "grid",

                                gridTemplateColumns:
                                "repeat(auto-fit, minmax(160px, 1fr))",

                                gap:
                                10,
                            }}
                        >
                            <div>
                                <small>
                                    Пополнения
                                </small>

                                <div
                                    style={{
                                        color:
                                        "var(--profit)",
                                    }}
                                >
                                    {
                                        formatMoney(
                                            performance.deposits_total
                                        )
                                    }
                                </div>
                            </div>

                            <div>
                                <small>
                                    Выводы
                                </small>

                                <div
                                    style={{
                                        color:
                                        "var(--loss)",
                                    }}
                                >
                                    {
                                        formatMoney(
                                            performance.withdrawals_total
                                        )
                                    }
                                </div>
                            </div>

                            <div>
                                <small>
                                    Чистые пополнения
                                </small>

                                <div>
                                    {
                                        formatMoney(
                                            performance.net_deposits
                                        )
                                    }
                                </div>
                            </div>

                            <div>
                                <small>
                                    Реализованная прибыль
                                </small>

                                <div>
                                    {
                                        formatMoney(
                                            performance.realized_profit
                                        )
                                    }
                                </div>
                            </div>

                            <div>
                                <small>
                                    Нереализованная
                                    {
                                        performance
                                            .unrealized_estimated
                                            ? " (оценка)"
                                            : ""
                                    }
                                </small>

                                <div>
                                    {
                                        formatMoney(
                                            performance.unrealized_profit
                                        )
                                    }
                                </div>
                            </div>

                            <div>
                                <small>
                                    В открытых позициях
                                </small>

                                <div>
                                    {
                                        formatMoney(
                                            performance.open_invested
                                        )
                                    }
                                </div>
                            </div>

                            <div>
                                <small>
                                    Баланс из истории
                                </small>

                                <div
                                    style={{
                                        fontWeight:
                                        700,
                                    }}
                                >
                                    {
                                        formatMoney(
                                            performance.historical_balance
                                        )
                                    }
                                </div>
                            </div>

                            <div>
                                <small>
                                    ROE (прибыль / пополнения)
                                </small>

                                <div
                                    style={{
                                        fontWeight:
                                        700,
                                    }}
                                >
                                    {
                                        formatPercent(
                                            performance.roe_percent
                                        )
                                    }
                                </div>
                            </div>

                            <div>
                                <small>
                                    ROI (позиции / баланс)
                                </small>

                                <div>
                                    {
                                        formatPercent(
                                            performance.roi_percent
                                        )
                                    }
                                </div>
                            </div>
                        </div>
                    )}

                    <div
                        style={{
                            marginTop:
                            12,

                            display:
                            "flex",

                            gap:
                            8,

                            flexWrap:
                            "wrap",

                            alignItems:
                            "flex-end",
                        }}
                    >
                        <label>
                            Сумма, ₽

                            <input
                                type=
                                    "number"

                                min=
                                    "0"

                                step=
                                    "0.01"

                                value={
                                    amount
                                }

                                onChange={
                                    event =>
                                        setAmount(
                                            event
                                                .target
                                                .value
                                        )
                                }

                                style={{
                                    width:
                                    140,

                                    marginTop:
                                    4,

                                    display:
                                    "block",
                                }}
                            />
                        </label>

                        <label>
                            Комментарий

                            <input
                                value={
                                    note
                                }

                                onChange={
                                    event =>
                                        setNote(
                                            event
                                                .target
                                                .value
                                        )
                                }

                                placeholder=
                                "перевод с карты"

                                style={{
                                    width:
                                    200,

                                    marginTop:
                                    4,

                                    display:
                                    "block",
                                }}
                            />
                        </label>

                        <button
                            type="button"

                            onClick={() => {
                                saveMovement(
                                    1
                                )
                            }}

                            disabled={
                                isSaving
                            }
                        >
                            {
                                isSaving
                                    ? "..."
                                    : "+ Пополнение"
                            }
                        </button>

                        <button
                            type="button"

                            onClick={() => {
                                saveMovement(
                                    -1
                                )
                            }}

                            disabled={
                                isSaving
                            }
                        >
                            {
                                isSaving
                                    ? "..."
                                    : "− Вывод"
                            }
                        </button>
                    </div>

                    {movements.length > 0 && (
                        <div
                            style={{
                                marginTop:
                                12,
                            }}
                        >
                            {
                                movements.map(
                                    movement => (
                                        <div
                                            key={
                                                (
                                                    movement.id
                                                    ?? movement.created_at
                                                )
                                            }

                                            style={{
                                                display:
                                                "flex",

                                                justifyContent:
                                                "space-between",

                                                gap:
                                                10,

                                                padding:
                                                "6px 0",

                                                borderTop:
                                                "1px solid var(--border)",

                                                fontSize:
                                                13,
                                            }}
                                        >
                                            <div>
                                                <b
                                                    style={{
                                                        color:
                                                        Number(
                                                            movement.amount
                                                        )
                                                        > 0
                                                            ? "var(--profit)"
                                                            : "var(--loss)",
                                                    }}
                                                >
                                                    {
                                                        Number(
                                                            movement.amount
                                                        )
                                                        > 0
                                                            ? "+ "
                                                            : "− "
                                                    }

                                                    {
                                                        formatMoney(
                                                            (
                                                                String(
                                                                    Math.abs(
                                                                        Number(
                                                                            movement.amount
                                                                        )
                                                                    )
                                                                )
                                                            )
                                                        )
                                                    }
                                                </b>

                                                {
                                                    movement.note
                                                    && (
                                                        <span
                                                            style={{
                                                                color:
                                                                "var(--text-muted)",
                                                            }}
                                                        >
                                                            {
                                                                " · "
                                                            }

                                                            {
                                                                movement.note
                                                            }
                                                        </span>
                                                    )
                                                }
                                            </div>

                                            <div
                                                style={{
                                                    color:
                                                    "var(--text-dim)",

                                                    fontSize:
                                                    11,

                                                    whiteSpace:
                                                    "nowrap",
                                                }}
                                            >
                                                {
                                                    formatTime(
                                                        movement.created_at
                                                    )
                                                }
                                            </div>
                                        </div>
                                    )
                                )
                            }
                        </div>
                    )}

                    {movements.length === 0 && (
                        <div
                            style={{
                                marginTop:
                                10,

                                color:
                                "var(--text-muted)",

                                fontSize:
                                13,
                            }}
                        >
                            Движений пока нет. Добавьте пополнения,
                            чтобы считать баланс и ROI из истории.
                        </div>
                    )}

                    {error && (
                        <div
                            style={{
                                marginTop:
                                10,

                                fontSize:
                                13,

                                color:
                                "var(--loss)",
                            }}
                        >
                            {
                                error
                            }
                        </div>
                    )}
                </>
            )}
        </div>
    )
}
