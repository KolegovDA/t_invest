type Props = {
    ticker: string
    levels: number
    quantity: string
    onLevelsChange: (value: number) => void
    onQuantityChange: (value: string) => void
    onSave: () => void
}


export function InstrumentSettingsForm({
    ticker,
    levels,
    quantity,
    onLevelsChange,
    onQuantityChange,
    onSave,
}: Props) {
    return (
        <div
            style={{
                background: "white",
                borderRadius: 18,
                padding: 16,
            }}
        >
            <h3 style={{ marginTop: 0 }}>
                {ticker}
            </h3>

            <label>
                Количество уровней
            </label>

            <div
                style={{
                    display: "flex",
                    gap: 8,
                    marginTop: 10,
                    marginBottom: 18,
                }}
            >
                {[10, 20, 30].map(value => (
                    <button
                        key={value}
                        onClick={() =>
                            onLevelsChange(value)
                        }
                        style={{
                            flex: 1,
                            padding: 13,
                            borderRadius: 12,
                            border:
                                levels === value
                                    ? "2px solid #2563eb"
                                    : "1px solid #d1d5db",
                            background:
                                levels === value
                                    ? "#eff6ff"
                                    : "white",
                            fontWeight: 600,
                        }}
                    >
                        {value}
                    </button>
                ))}
            </div>

            <label>
                Базовый лот
            </label>

            <input
                type="text"
                inputMode="numeric"
                value={quantity}
                onChange={event =>
                    onQuantityChange(
                        event.target.value.replace(
                            /\D/g,
                            ""
                        )
                    )
                }
                style={{
                    width: "100%",
                    boxSizing: "border-box",
                    padding: 14,
                    marginTop: 8,
                    marginBottom: 20,
                    borderRadius: 12,
                    border: "1px solid #d1d5db",
                    fontSize: 17,
                }}
            />

            <button
                onClick={onSave}
                style={{
                    width: "100%",
                    padding: 15,
                    border: "none",
                    borderRadius: 13,
                    background: "#2563eb",
                    color: "white",
                    fontSize: 17,
                    fontWeight: 600,
                }}
            >
                Сохранить
            </button>
        </div>
    )
}
