type Props = {
    newTicker: string
    newLevels: number
    newBaseQuantity: string
    onTickerChange: (value: string) => void
    onLevelsChange: (value: number) => void
    onBaseQuantityChange: (value: string) => void
    onSave: () => void
    onCancel: () => void
}

export function AddInstrumentForm({
    newTicker,
    newLevels,
    newBaseQuantity,
    onTickerChange,
    onLevelsChange,
    onBaseQuantityChange,
    onSave,
    onCancel,
}: Props) {
    return (
        <div
            style={{
                background: "white",
                borderRadius: 16,
                padding: 16,
                marginBottom: 12,
                boxShadow: "0 6px 16px rgba(0,0,0,0.06)",
            }}
        >
            <h3 style={{ marginTop: 0 }}>Новый инструмент</h3>

            <label>Тикер</label>

            <input
                value={newTicker}
                onChange={event => onTickerChange(event.target.value)}
                placeholder="SBER"
                style={{
                    width: "100%",
                    padding: 12,
                    marginTop: 6,
                    marginBottom: 12,
                    borderRadius: 10,
                    border: "1px solid #ddd",
                    boxSizing: "border-box",
                    fontSize: 16,
                }}
            />

            <label>Количество уровней</label>

            <div
                style={{
                    display: "flex",
                    gap: 8,
                    marginTop: 8,
                    marginBottom: 12,
                }}
            >
                {[10, 20, 30].map(level => (
                    <button
                        key={level}
                        onClick={() => onLevelsChange(level)}
                        style={{
                            flex: 1,
                            padding: 12,
                            borderRadius: 10,
                            border:
                                newLevels === level
                                    ? "2px solid #111827"
                                    : "1px solid #ddd",
                            background:
                                newLevels === level ? "#eef2ff" : "white",
                        }}
                    >
                        {level}
                    </button>
                ))}
            </div>

            <label>Базовый лот</label>

            <input
                type="text"
                inputMode="numeric"
                value={newBaseQuantity}
                onChange={event =>
                    onBaseQuantityChange(
                        event.target.value.replace(/\D/g, "")
                    )
                }
                style={{
                    width: "100%",
                    padding: 12,
                    marginTop: 6,
                    marginBottom: 12,
                    borderRadius: 10,
                    border: "1px solid #ddd",
                    boxSizing: "border-box",
                    fontSize: 16,
                }}
            />

            <div style={{ display: "flex", gap: 8 }}>
                <button
                    onClick={onSave}
                    style={{
                        flex: 1,
                        padding: 12,
                        borderRadius: 10,
                        border: "none",
                        background: "#16a34a",
                        color: "white",
                    }}
                >
                    Сохранить
                </button>

                <button
                    onClick={onCancel}
                    style={{
                        flex: 1,
                        padding: 12,
                        borderRadius: 10,
                        border: "1px solid #ddd",
                        background: "white",
                    }}
                >
                    Отмена
                </button>
            </div>
        </div>
    )
}
