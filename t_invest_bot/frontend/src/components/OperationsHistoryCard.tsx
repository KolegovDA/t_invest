import type {
    OperationLogEntry,
} from "../types"


const eventTypeLabels: Record<
    string,
    string
> = {
    BUY:
    "Покупка",

    SELL:
    "Продажа",

    ORDER_PLACED:
    "Ордер",

    ACCOUNT_ADDED:
    "Счёт добавлен",

    ACCOUNT_UPDATED:
    "Счёт обновлён",

    ACCOUNT_REMOVED:
    "Счёт удалён",

    PHANTOMS_REMOVED:
    "Фантомы удалены",

    DEPOSIT:
    "Пополнение",

    WITHDRAWAL:
    "Вывод",
}


const eventTypeColors: Record<
    string,
    string
> = {
    BUY: "#15803d",

    SELL: "#b91c1c",

    ORDER_PLACED: "#6b7280",

    ACCOUNT_ADDED: "#2563eb",

    ACCOUNT_UPDATED: "#2563eb",

    ACCOUNT_REMOVED: "#9a3412",

    PHANTOMS_REMOVED: "#9a3412",

    DEPOSIT: "#15803d",

    WITHDRAWAL: "#b91c1c",
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


function formatEventColor(
    eventType: string
): string {
    return (
        eventTypeColors[
            eventType
        ]
        ?? "#374151"
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
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
            }
        )
    )
}


export function OperationsHistoryCard({
    operations,
}: {
    operations:
    OperationLogEntry[]
}) {
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
                    10,
                }}
            >
                История операций
            </h3>

            {operations.length === 0 ? (
                <div
                    style={{
                        color:
                        "#6b7280",

                        fontSize:
                        13,
                    }}
                >
                    Операций пока нет: сделки, ордера и действия со счетами появятся здесь.
                </div>
            ) : (
                operations.map(
                    (
                        operation,
                        index,
                    ) => (
                        <div
                            key={
                                operation.created_at
                                + "-"
                                + operation.event_type
                                + "-"
                                + index
                            }

                            style={{
                                display:
                                "flex",

                                justifyContent:
                                "space-between",

                                alignItems:
                                "flex-start",

                                gap:
                                10,

                                padding:
                                "9px 0",

                                borderTop:
                                index
                                === 0
                                ? "none"
                                : "1px solid #e5e7eb",
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
                                        display:
                                        "flex",

                                        alignItems:
                                        "center",

                                        gap:
                                        8,

                                        marginBottom:
                                        3,
                                    }}
                                >
                                    <span
                                        style={{
                                            fontWeight:
                                            700,

                                            color:
                                            formatEventColor(
                                                operation.event_type
                                            ),

                                            fontSize:
                                            13,
                                        }}
                                    >
                                        {
                                            formatEventType(
                                                operation.event_type
                                            )
                                        }
                                    </span>

                                    {
                                        operation.ticker
                                        && (
                                            <span
                                                style={{
                                                    fontWeight:
                                                    700,

                                                    fontSize:
                                                    13,
                                                }}
                                            >
                                                {
                                                    operation.ticker
                                                }
                                            </span>
                                        )
                                    }
                                </div>

                                <div
                                    style={{
                                        color:
                                        "#6b7280",

                                        fontSize:
                                        12,

                                        wordBreak:
                                        "break-word",
                                    }}
                                >
                                    {
                                        operation.details
                                    }
                                </div>
                            </div>

                            <div
                                style={{
                                    color:
                                    "#9ca3af",

                                    fontSize:
                                    11,

                                    whiteSpace:
                                    "nowrap",
                                }}
                            >
                                {
                                    formatTime(
                                        operation.created_at
                                    )
                                }
                            </div>
                        </div>
                    )
                )
            )}
        </div>
    )
}
