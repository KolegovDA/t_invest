import type {
    Dashboard,
} from "../types"


type Props = {
    dashboard: Dashboard
}


function formatMoney(
    value: number | null | undefined
): string {
    if (
        value === null
        || value === undefined
    ) {
        return "—"
    }

    return (
        value.toLocaleString(
            "ru-RU",
            {
                minimumFractionDigits: 0,
                maximumFractionDigits: 2,
            }
        )
        + " ₽"
    )
}


function MetricRow({
    label,
    value,
    emphasis = false,
}: {
    label: string
    value: string
    emphasis?: boolean
}) {
    return (
        <div
            style={{
                display: "flex",
                justifyContent: "space-between",
                gap: 12,
                padding: "9px 0",
                borderBottom: "1px solid #f3f4f6",
            }}
        >
            <span
                style={{
                    color: emphasis
                        ? "#111827"
                        : "#6b7280",
                    fontWeight: emphasis
                        ? 600
                        : 400,
                }}
            >
                {label}
            </span>

            <b
                style={{
                    textAlign: "right",
                    color: "#111827",
                }}
            >
                {value}
            </b>
        </div>
    )
}


export function DashboardCard({
    dashboard,
}: Props) {
    const realized =
        dashboard.realized_profit
        ?? 0

    const unrealized =
        dashboard.unrealized_profit
        ?? 0

    return (
        <div
            style={{
                background: "white",
                borderRadius: 16,
                padding: 16,
                marginBottom: 16,
                boxShadow:
                    "0 6px 16px rgba(0,0,0,0.06)",
            }}
        >
            <h3
                style={{
                    margin: "0 0 8px",
                }}
            >
                Портфель стратегии
            </h3>

            <MetricRow
                label="Счетов"
                value={
                    String(
                        dashboard.accounts
                    )
                }
            />

            <MetricRow
                label="Расчётный капитал при запуске"
                value={
                    formatMoney(
                        dashboard.capital
                    )
                }
                emphasis
            />

            <MetricRow
                label="Свободные средства счёта"
                value={
                    formatMoney(
                        dashboard.available_cash
                    )
                }
            />

            <MetricRow
                label="Вложено в открытые позиции"
                value={
                    formatMoney(
                        dashboard.invested_cash
                    )
                }
            />

            <MetricRow
                label="Зарезервировано под BUY-заявки"
                value={
                    formatMoney(
                        dashboard.reserved_cash
                    )
                }
            />

            <MetricRow
                label="Активных позиций"
                value={
                    String(
                        dashboard.active_positions
                    )
                }
            />

            <div
                style={{
                    marginTop: 18,
                }}
            >
                <h4
                    style={{
                        margin: "0 0 6px",
                    }}
                >
                    Результат торговли
                </h4>

                <MetricRow
                    label="Реализованная прибыль"
                    value={
                        formatMoney(
                            realized
                        )
                    }
                />

                <MetricRow
                    label="Плавающий PnL"
                    value={
                        formatMoney(
                            unrealized
                        )
                    }
                />

                <MetricRow
                    label="Итоговый PnL"
                    value={
                        formatMoney(
                            dashboard.profit
                        )
                    }
                    emphasis
                />
            </div>

            <div
                style={{
                    marginTop: 12,
                    padding: 10,
                    borderRadius: 10,
                    background: "#f9fafb",
                    color: "#6b7280",
                    fontSize: 12,
                    lineHeight: 1.45,
                }}
            >
                Расчётный капитал фиксируется в момент запуска стратегии.
                Вложено — фактически купленные открытые позиции с BUY-комиссией.
                Резерв — только деньги под уже выставленные, но ещё не исполненные
                BUY-заявки. Плавающий PnL меняется вместе с рыночной ценой.
            </div>
        </div>
    )
}
