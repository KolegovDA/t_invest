import {
    useEffect,
    useState,
} from "react"

import {
    getReconciliationEvents,
} from "../api"

import type {
    ReconciliationEvent,
} from "../types"


const eventTypeLabels: Record<
    string,
    string
> = {
    ORDER_RECONCILE:
    "Сверка заявок",

    POSITION_CLEARED:
    "Позиции закрыты вне бота",

    POSITION_MISMATCH:
    "Расхождение позиций",

    RECONCILE_ERROR:
    "Ошибка сверки",
}


function formatEventType(
    eventType: string
): string {
    return (
        eventTypeLabels[
            eventType
        ]
        ?? eventType
    )
}


function eventColor(
    eventType: string
): string {
    if (
        eventType
        === "RECONCILE_ERROR"
        || eventType
        === "POSITION_MISMATCH"
    ) {
        return "var(--loss)"
    }

    return "var(--accent)"
}


export function ReconciliationCard() {
    const [
        events,
        setEvents,
    ] = useState<
        ReconciliationEvent[]
    >([])

    const [
        countsByType,
        setCountsByType,
    ] = useState<
        Record<string, number>
    >({})

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
                getReconciliationEvents(
                    50
                )
                    .then(
                        data => {
                            if (
                                cancelled
                            ) {
                                return
                            }

                            setEvents(
                                data.events
                            )

                            setCountsByType(
                                data.counts_by_type
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

    return (
        <div
            style={{
                background: "var(--card)",
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
                Журнал сверки
            </h2>

            <p
                style={{
                    color: "var(--text-muted)",
                    fontSize: 13,
                }}
            >
                События синхронизации состояния бота с брокером: усыновление заявок, откат фантомных уровней, расхождения позиций.
            </p>

            {Object.keys(
                countsByType
            ).length > 0 && (
                <div
                    style={{
                        display:
                        "flex",
                        flexWrap:
                        "wrap",
                        gap: 8,
                        marginBottom: 12,
                    }}
                >
                    {Object.entries(
                        countsByType
                    ).map(
                        ([
                            eventType,
                            count,
                        ]) => (
                            <span
                                key={
                                    eventType
                                }
                                style={{
                                    padding:
                                    "4px 10px",
                                    borderRadius:
                                    999,
                                    background:
                                    "var(--accent-soft)",
                                    color:
                                    eventColor(
                                        eventType
                                    ),
                                    fontSize:
                                    12,
                                    fontWeight:
                                    700,
                                }}
                            >
                                {
                                    formatEventType(
                                        eventType
                                    )
                                }
                                {": "}
                                {
                                    count
                                }
                            </span>
                        )
                    )}
                </div>
            )}

            {error && (
                <div
                    style={{
                        color:
                        "var(--loss)",
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
            && events.length
            === 0 && (
                <p>
                    Расхождений не найдено — сверка проходит без событий.
                </p>
            )}

            {events.map(
                (
                    event,
                    index
                ) => (
                    <div
                        key={
                            `${
                                event.created_at
                            }-${
                                index
                            }`
                        }
                        style={{
                            borderTop:
                            "1px solid var(--border)",
                            paddingTop: 10,
                            marginTop: 10,
                            fontSize: 13,
                        }}
                    >
                        <div
                            style={{
                                display:
                                "flex",
                                justifyContent:
                                "space-between",
                                gap: 8,
                            }}
                        >
                            <b
                                style={{
                                    color: eventColor(
                                        event.event_type
                                    ),
                                }}
                            >
                                {
                                    formatEventType(
                                        event.event_type
                                    )
                                }
                            </b>

                            <span
                                style={{
                                    color:
                                    "var(--text-dim)",
                                    fontSize:
                                    11,
                                }}
                            >
                                {
                                    event.created_at.slice(
                                        0,
                                        19
                                    ).replace(
                                        "T",
                                        " "
                                    )
                                }
                            </span>
                        </div>

                        <div
                            style={{
                                color:
                                "var(--text)",
                                marginTop: 4,
                            }}
                        >
                            {
                                event.instrument_id
                                ?? "—"
                            }
                        </div>

                        <div
                            style={{
                                color:
                                "var(--text-muted)",
                                marginTop: 2,
                                wordBreak:
                                "break-word",
                            }}
                        >
                            {
                                event.details
                            }
                        </div>
                    </div>
                )
            )}
        </div>
    )
}
