import type { StartPlan, StartSandboxResult } from "../types"

type Props = {
    startPlan: StartPlan
    startResult: StartSandboxResult | null
    onStart: () => void
}

export function StartPlanCard({
    startPlan,
    startResult,
    onStart,
}: Props) {
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
            <h2>Стартовый расчет</h2>

            <p>
                Требуется всего:{" "}
                <b>{Number(startPlan.total_required).toLocaleString()} ₽</b>
            </p>

            <p>
                Доступно:{" "}
                <b>{Number(startPlan.available_cash).toLocaleString()} ₽</b>
            </p>

            <p>
                Остаток:{" "}
                <b>{Number(startPlan.remaining_cash).toLocaleString()} ₽</b>
            </p>

            <p>
                Не хватает:{" "}
                <b>{Number(startPlan.missing_cash).toLocaleString()} ₽</b>
            </p>

            <p>
                Использование капитала:{" "}
                <b>
                    {Number(
                        startPlan.capital_utilization_percent
                    ).toFixed(2)}
                    %
                </b>
            </p>

            <p>
                Можно запустить:{" "}
                <b>{startPlan.can_start ? "да" : "нет"}</b>
            </p>

            <p>
                Принудительный запуск:{" "}
                <b>
                    {startPlan.can_start_forced
                        ? "разрешен"
                        : "запрещен"}
                </b>
            </p>

            <h3>По инструментам</h3>

            {startPlan.instruments.map(instrument => (
                <div
                    key={instrument.ticker}
                    style={{
                        borderTop: "1px solid #eee",
                        paddingTop: 10,
                        marginTop: 10,
                    }}
                >
                    <b>{instrument.ticker}</b>
                    <p>Уровней: {instrument.levels}</p>
                    <p>Базовый лот: {instrument.quantity}</p>
                    <p>
                        Цена:{" "}
                        {Number(instrument.last_price).toLocaleString()} ₽
                    </p>
                    <p>
                        Нужно:{" "}
                        {Number(
                            instrument.required_deposit
                        ).toLocaleString()} ₽
                    </p>
                </div>
            ))}

            <button
                onClick={onStart}
                style={{
                    width: "100%",
                    padding: 16,
                    marginTop: 12,
                    fontSize: 18,
                    borderRadius: 14,
                    border: "none",
                    background: startPlan.can_start
                        ? "#16a34a"
                        : "#f97316",
                    color: "white",
                }}
            >
                {startPlan.can_start
                    ? "Запустить стратегию"
                    : "Запустить принудительно"}
            </button>

            {startResult && (
                <div
                    style={{
                        marginTop: 12,
                        padding: 12,
                        borderRadius: 12,
                        background:
                            startResult.real_sandbox_status === "started"
                                ? "#dcfce7"
                                : "#ffedd5",
                    }}
                >
                    <p>
                        Статус запуска: <b>{startResult.status}</b>
                    </p>
                    <p>
                        Режим: <b>{startResult.mode}</b>
                    </p>
                    <p>
                        Реальный sandbox:{" "}
                        <b>{startResult.real_sandbox_status}</b>
                    </p>
                </div>
            )}
        </div>
    )
}
