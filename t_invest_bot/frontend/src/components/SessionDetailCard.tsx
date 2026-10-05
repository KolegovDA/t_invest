import type { ActiveSession } from "../types"
import { SessionsCard } from "./SessionsCard"

type Props = {
    session: ActiveSession | null
    onClose: () => void
    onStop: (ticker: string) => void
}

export function SessionDetailCard({
    session,
    onClose,
    onStop,
}: Props) {
    if (!session) {
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
            <div
                style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                }}
            >
                <h2 style={{ marginTop: 0 }}>
                    {session.ticker}
                </h2>

                <button
                    onClick={onClose}
                    style={{
                        border: "none",
                        background: "transparent",
                        fontSize: 20,
                    }}
                >
                    ×
                </button>
            </div>

            <SessionsCard sessions={[session]} onOpen={() => {}} />
            <div
                style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                    gap: 12,
                    marginTop: 12,
                }}
            >
                {[
                    ["Цена", session.current_price],
                    ["Реализовано", session.realized_profit],
                    ["Нереализовано", session.unrealized_profit],
                    ["Общая прибыль", session.total_profit],
                ].map(([label, value]) => (
                    <div key={label} style={{ padding: 12, borderRadius: 12, background: "var(--card-soft)" }}>
                        <div style={{ fontSize: 12, color: "var(--text-muted)" }}>{label}</div>
                        <b>{Number(value).toLocaleString("ru-RU", { maximumFractionDigits: 2 })} ₽</b>
                    </div>
                ))}
            </div>

            <button
                onClick={() => onStop(session.ticker)}
                disabled={session.status === "STOPPED"}
                style={{
                    width: "100%",
                    padding: 16,
                    marginTop: 12,
                    fontSize: 18,
                    borderRadius: 14,
                    border: "none",
                    background:
                        session.status === "STOPPED"
                            ? "var(--text-dim)"
                            : "var(--loss)",
                    color: "white",
                }}
            >
                {session.status === "STOPPED"
                    ? "Остановлено"
                    : "Остановить"}
            </button>
        </div>
    )
}
