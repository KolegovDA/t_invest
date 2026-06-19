import type { Dashboard } from "../types"

type Props = {
    dashboard: Dashboard
}

export function DashboardCard({ dashboard }: Props) {
    return (
        <div
            style={{
                background: "white",
                borderRadius: 16,
                padding: 16,
                marginBottom: 16,
                boxShadow: "0 6px 16px rgba(0,0,0,0.06)",
            }}
        >
            <p>Счетов: {dashboard.accounts}</p>
            <p>Капитал: {dashboard.capital.toLocaleString()} ₽</p>
            <p>Активных позиций: {dashboard.active_positions}</p>
            <p>Прибыль: {dashboard.profit} ₽</p>
        </div>
    )
}
