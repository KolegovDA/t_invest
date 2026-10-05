import type { ActiveSession } from "../types"

type Props = {
    sessions: ActiveSession[]
    onOpen: (ticker: string) => void
}

export function SessionsCard({
    sessions,
    onOpen,
}: Props) {
    if (sessions.length === 0) {
        return null
    }

    return (
        <div
            style={{
                background: "var(--card)",
                borderRadius: 16,
                padding: 16,
                marginTop: 16,
                boxShadow: "0 6px 16px rgba(0,0,0,0.06)",
            }}
        >
            <h2
                style={{
                    margin: "0 0 4px",
                    fontSize: 18,
                }}
            >
                Активные сессии
            </h2>

            {sessions.map((session, index) => {
                const profit = (
                    Number(
                        session.total_profit
                        ?? 0
                    )
                )

                const profitColor = (
                    profit > 0
                        ? "var(--profit)"
                        : profit < 0
                            ? "var(--loss)"
                            : "var(--text)"
                )

                return (
                    <div
                        key={session.ticker}
                        onClick={() => {
                            onOpen(
                                session.ticker
                            )
                        }}
                        style={{
                            display: "flex",
                            alignItems: "center",
                            gap: 12,
                            padding: "14px 0",
                            borderTop: (
                                index
                                === 0
                                    ? "none"
                                    : "1px solid var(--border)"
                            ),
                            cursor: "pointer",
                        }}
                    >
                        <div
                            style={{
                                width: 36,
                                height: 36,
                                borderRadius: "50%",
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                background: "var(--card-soft)",
                                color: "var(--accent)",
                                fontWeight: 700,
                                fontSize: 15,
                                flexShrink: 0,
                            }}
                        >
                                {
                                    (
                                        session.ticker
                                        ?? ""
                                    ).trim().charAt(
                                        0
                                    ).toUpperCase()

                                    || "С"
                                }
                        </div>

                        <div
                            style={{
                                flex: 1,
                                minWidth: 0,
                            }}
                        >
                            <div
                                style={{
                                    fontWeight: 600,
                                    fontSize: 15,
                                    color: "var(--text)",
                                }}
                            >
                                {
                                    session.ticker
                                }
                            </div>

                            <div
                                style={{
                                    marginTop: 2,
                                    fontSize: 12,
                                    color: "var(--text-muted)",
                                }}
                            >
                                {
                                    session.status
                                }

                                {" · "}

                                Уровней: {
                                    session.levels
                                }

                                {" · "}

                                Лот: {
                                    session.quantity
                                }

                                {" · "}

                                Позиций: {
                                    session.positions
                                }
                            </div>
                        </div>

                        <div
                            style={{
                                textAlign: "right",
                                flexShrink: 0,
                            }}
                        >
                            <div
                                style={{
                                    fontWeight: 700,
                                    fontSize: 14,
                                    color: profitColor,
                                }}
                            >
                                {
                                    profit.toLocaleString(
                                        "ru-RU",
                                        {
                                            minimumFractionDigits: 2,
                                            maximumFractionDigits: 2,
                                        }
                                    )
                                }

                                {" ₽"}
                            </div>

                            <div
                                style={{
                                    marginTop: 2,
                                    fontSize: 11,
                                    color: "var(--text-dim)",
                                }}
                            >
                                прибыль
                            </div>
                        </div>

                        <span
                            style={{
                                fontSize: 18,
                                color: "var(--text-dim)",
                                flexShrink: 0,
                            }}
                        >
                            ›
                        </span>
                    </div>
                )
            })}
        </div>
    )
}
