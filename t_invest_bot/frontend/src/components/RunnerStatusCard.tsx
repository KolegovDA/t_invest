import type { RunnerStatus } from "../types"

type Props = {
    runners: RunnerStatus[]
}

export function RunnerStatusCard({
    runners,
}: Props) {
    if (runners.length === 0) {
        return (
            <div style={cardStyle}>
                <h2 style={{ marginTop: 0 }}>
                    Runner
                </h2>

                <p>
                    Фоновый runner не запущен
                </p>
            </div>
        )
    }

    return (
        <div style={cardStyle}>
            <h2 style={{ marginTop: 0 }}>
                Runner
            </h2>

            {runners.map(
                (runner, index) => (
                    <div
                        key={index}
                        style={{
                            marginTop: 12,
                        }}
                    >
                        <p>
                            Статус:{" "}
                            <b>
                                {runner.is_running
                                    ? "RUNNING"
                                    : "STOPPED"}
                            </b>
                        </p>

                        <p>
                            Последний тик:{" "}
                            <b>
                                {runner.last_tick_at
                                    ? new Date(
                                        runner.last_tick_at
                                    ).toLocaleString()
                                    : "—"}
                            </b>
                        </p>

                        <p>
                            Тиков:{" "}
                            <b>
                                {runner.ticks_count}
                            </b>
                        </p>

                        <p>
                            Получено цен:{" "}
                            <b>
                                {
                                    runner.prices_checked_total
                                }
                            </b>
                        </p>

                        <p>
                            Выставлено ордеров:{" "}
                            <b>
                                {
                                    runner.orders_placed_total
                                }
                            </b>
                        </p>

                        <p>
                            Исполнений:{" "}
                            <b>
                                {
                                    runner.executions_total
                                }
                            </b>
                        </p>

                        <p>
                            Последняя ошибка:{" "}
                            <b>
                                {runner.last_error ??
                                    "—"}
                            </b>
                        </p>
                    </div>
                )
            )}
        </div>
    )
}

const cardStyle = {
    background: "white",
    borderRadius: 18,
    padding: 16,
    marginBottom: 16,
    boxShadow:
        "0 4px 14px rgba(0,0,0,0.05)",
}
