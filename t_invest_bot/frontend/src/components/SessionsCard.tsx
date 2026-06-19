import type { ActiveSession } from "../types"

type Props = {
    sessions: ActiveSession[]
}

export function SessionsCard({ sessions }: Props) {
    if (sessions.length === 0) {
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
            <h2>Активные сессии</h2>

            {sessions.map(session => (
                <div
                    key={session.ticker}
                    style={{
                        borderTop: "1px solid #eee",
                        paddingTop: 10,
                        marginTop: 10,
                    }}
                >
                    <b>{session.ticker}</b>
                    <p>Статус: {session.status}</p>
                    <p>Уровней: {session.levels}</p>
                    <p>Базовый лот: {session.quantity}</p>
                    <p>Позиции: {session.positions}</p>
                    <p>Прибыль: {session.profit} ₽</p>
                </div>
            ))}
        </div>
    )
}
