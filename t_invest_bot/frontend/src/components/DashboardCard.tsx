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
                maximumFractionDigits: 2,
            }
        )
        + " ₽"
    )
}


export function DashboardCard({
    dashboard,
}: Props) {
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
            <p>
                Счетов:{" "}
                <b>
                    {dashboard.accounts}
                </b>
            </p>

            <p>
                Первоначальный депозит:{" "}
                <b>
                    {formatMoney(
                        dashboard.capital
                    )}
                </b>
            </p>

            <p>
                Свободные средства:{" "}
                <b>
                    {formatMoney(
                        dashboard.available_cash
                    )}
                </b>
            </p>

            <p>
                Зарезервировано:{" "}
                <b>
                    {formatMoney(
                        dashboard.reserved_cash
                    )}
                </b>
            </p>

            <p>
                Активных позиций:{" "}
                <b>
                    {
                        dashboard
                            .active_positions
                    }
                </b>
            </p>

            <p>
                Прибыль:{" "}
                <b>
                    {formatMoney(
                        dashboard.profit
                    )}
                </b>
            </p>
        </div>
    )
}
