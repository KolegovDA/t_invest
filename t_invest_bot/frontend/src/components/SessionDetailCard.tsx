import type { ActiveSession } from "../types"

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
                background: "white",
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

            <p>Статус: {session.status}</p>
            <p>Цена: {session.current_price.toLocaleString()} ₽</p>
            <p>Уровней: {session.levels}</p>
            <p>Базовый лот: {session.quantity}</p>
            <p>Открытых позиций: {session.positions}</p>
            <p>
                Реализовано:{" "}
                {session.realized_profit.toLocaleString()} ₽
            </p>
            <p>
                Нереализовано:{" "}
                {session.unrealized_profit.toLocaleString()} ₽
            </p>
            <p>
                Общая прибыль:{" "}
                <b>{session.total_profit.toLocaleString()} ₽</b>
            </p>

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
                            ? "#9ca3af"
                            : "#dc2626",
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
