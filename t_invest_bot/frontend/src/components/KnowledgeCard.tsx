import {
    useEffect,
    useState,
} from "react"

import {
    getKnowledgeInstruments,
} from "../api"

import type {
    KnowledgeInstrument,
} from "../types"


function profitColor(
    value: string
): string {
    return (
        Number(value)
        < 0

        ? "#b91c1c"

        : "#15803d"
    )
}


export function KnowledgeCard() {
    const [
        instruments,
        setInstruments,
    ] = useState<
        KnowledgeInstrument[]
    >([])

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

            function load() {
                getKnowledgeInstruments()
                    .then(
                        data => {
                            if (
                                cancelled
                            ) {
                                return
                            }

                            setInstruments(
                                data.instruments
                            )

                            setError(
                                null
                            )
                        }
                    )
                    .catch(
                        loadError => {
                            if (
                                cancelled
                            ) {
                                return
                            }

                            setError(
                                loadError instanceof Error
                                ? loadError.message
                                : String(
                                    loadError
                                )
                            )
                        }
                    )
                    .finally(
                        () => {
                            if (
                                !cancelled
                            ) {
                                setIsLoading(
                                    false
                                )
                            }
                        }
                    )
            }

            load()

            const intervalId =
                window.setInterval(
                    load,
                    5000
                )

            return () => {
                cancelled =
                true

                window.clearInterval(
                    intervalId
                )
            }
        },

        []
    )

    const totalCycles =
        instruments.reduce(
            (
                sum,
                instrument
            ) =>
                sum
                + instrument.total_cycles,

            0
        )

    const totalProfit =
        instruments.reduce(
            (
                sum,
                instrument
            ) =>
                sum
                + Number(
                    instrument.total_profit
                ),

            0
        )

    return (
        <div
            style={{
                background:
                "white",
                borderRadius: 16,
                padding: 16,
                marginBottom: 16,
                boxShadow:
                "0 6px 16px rgba(0,0,0,0.06)",
            }}
        >
            <h2
                style={{
                    marginTop: 0,
                }}
            >
                База знаний (v1.1)
            </h2>

            <p
                style={{
                    color: "#6b7280",
                    fontSize: 13,
                }}
            >
                Локальная статистика циклов по инструментам: используется для бонуса ConfidenceScore и будущих рейтингов.
            </p>

            {instruments.length > 0 && (
                <div
                    style={{
                        display: "flex",
                        flexWrap: "wrap",
                        gap: 8,
                        marginBottom: 12,
                    }}
                >
                    <span
                        style={{
                            padding: "4px 10px",
                            borderRadius: 999,
                            background: "#eff6ff",
                            color: "#2563eb",
                            fontSize: 12,
                            fontWeight: 700,
                        }}
                    >
                        Инструментов:{" "}
                        {
                            instruments.length
                        }
                    </span>

                    <span
                        style={{
                            padding: "4px 10px",
                            borderRadius: 999,
                            background: "#eff6ff",
                            color: "#2563eb",
                            fontSize: 12,
                            fontWeight: 700,
                        }}
                    >
                        Циклов:{" "}
                        {
                            totalCycles
                        }
                    </span>

                    <span
                        style={{
                            padding: "4px 10px",
                            borderRadius: 999,
                            background: "#f0fdf4",
                            color: profitColor(
                                String(
                                    totalProfit
                                )
                            ),
                            fontSize: 12,
                            fontWeight: 700,
                        }}
                    >
                        Итог:{" "}
                        {
                            totalProfit.toFixed(
                                2
                            )
                        }
                    </span>
                </div>
            )}

            {error && (
                <div
                    style={{
                        color: "#b91c1c",
                        fontSize: 13,
                        marginBottom: 8,
                    }}
                >
                    {
                        error
                    }
                </div>
            )}

            {isLoading && (
                <p>
                    Загрузка...
                </p>
            )}

            {!isLoading
            && instruments.length
            === 0 && (
                <p>
                    Пока нет данных — статистика появится после первых завершённых циклов сделок.
                </p>
            )}

            {instruments.map(
                instrument => (
                    <div
                        key={
                            instrument.instrument_id
                        }
                        style={{
                            borderTop:
                            "1px solid #eee",
                            paddingTop: 10,
                            marginTop: 10,
                            fontSize: 13,
                        }}
                    >
                        <div
                            style={{
                                display: "flex",
                                justifyContent: "space-between",
                                fontWeight: 700,
                            }}
                        >
                            <span>
                                {
                                    instrument.instrument_id
                                }
                            </span>

                            <span
                                style={{
                                    color: profitColor(
                                        instrument.total_profit
                                    ),
                                }}
                            >
                                {
                                    instrument.total_profit
                                }
                            </span>
                        </div>

                        <div
                            style={{
                                display: "flex",
                                flexWrap: "wrap",
                                gap: 12,
                                color: "#6b7280",
                                marginTop: 4,
                            }}
                        >
                            <span>
                                Циклы:{" "}
                                {
                                    instrument.total_cycles
                                }

                                {" ("}

                                {
                                    instrument.profitable_cycles
                                }

                                {"+"}

                                {" / "}

                                {
                                    instrument.losing_cycles
                                }

                                {"−)"}
                            </span>

                            <span>
                                Средний цикл:{" "}
                                {
                                    instrument.average_cycle_profit
                                }
                            </span>

                            <span>
                                Просадка:{" "}
                                {
                                    instrument.max_drawdown
                                }
                            </span>

                            <span>
                                Сделок:{" "}
                                {
                                    instrument.total_trades
                                }
                            </span>
                        </div>
                    </div>
                )
            )}
        </div>
    )
}
