import type { ApiUsage } from "../types"

type Props = {
    apiUsage: ApiUsage | null
}

export function ApiUsageCard({
    apiUsage,
}: Props) {
    if (!apiUsage) {
        return null
    }

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
            <h2 style={{ marginTop: 0 }}>API нагрузка</h2>

            <p>
                Событий:{" "}
                <b>{apiUsage.events_count.toLocaleString()}</b>
            </p>

            <p>
                Вес запросов:{" "}
                <b>{apiUsage.total_weight.toLocaleString()}</b>
            </p>

            <h3>Операции</h3>

            {Object.keys(apiUsage.by_operation).length === 0 && (
                <p>Пока нет данных</p>
            )}

            {Object.entries(apiUsage.by_operation).map(
                ([operation, weight]) => (
                    <div
                        key={operation}
                        style={{
                            display: "flex",
                            justifyContent: "space-between",
                            borderTop: "1px solid #eee",
                            paddingTop: 8,
                            marginTop: 8,
                        }}
                    >
                        <span>{operation}</span>
                        <b>{weight}</b>
                    </div>
                )
            )}
        </div>
    )
}
