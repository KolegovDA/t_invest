import type { Instrument } from "../types"

type Props = {
    instrument: Instrument
    isEditing: boolean
    editLevels: number
    editQuantity: string
    onStartEdit: (instrument: Instrument) => void
    onRemove: (ticker: string) => void
    onEditLevelsChange: (value: number) => void
    onEditQuantityChange: (value: string) => void
    onSaveEdit: () => void
    onCancelEdit: () => void
}

export function InstrumentCard({
    instrument,
    isEditing,
    editLevels,
    editQuantity,
    onStartEdit,
    onRemove,
    onEditLevelsChange,
    onEditQuantityChange,
    onSaveEdit,
    onCancelEdit,
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
            <h3 style={{ marginTop: 0 }}>{instrument.ticker}</h3>

            <p>Уровней: {instrument.levels}</p>
            <p>Базовый лот: {instrument.quantity ?? 1}</p>
            <p>Текущая цена: {instrument.price.toLocaleString()} ₽</p>
            <p>
                Требуется капитал:{" "}
                {instrument.required_capital.toLocaleString()} ₽
            </p>

            {isEditing && (
                <div style={{ marginTop: 12 }}>
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
                                onClick={() => onEditLevelsChange(level)}
                                style={{
                                    flex: 1,
                                    padding: 12,
                                    borderRadius: 10,
                                    border:
                                        editLevels === level
                                            ? "2px solid #111827"
                                            : "1px solid #ddd",
                                    background:
                                        editLevels === level
                                            ? "#eef2ff"
                                            : "white",
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
                        value={editQuantity}
                        onChange={event =>
                            onEditQuantityChange(
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

                    <div
                        style={{
                            display: "flex",
                            gap: 8,
                            marginBottom: 12,
                        }}
                    >
                        <button
                            onClick={onSaveEdit}
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
                            onClick={onCancelEdit}
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
            )}

            <div style={{ display: "flex", gap: 8 }}>
                <button
                    onClick={() => onStartEdit(instrument)}
                    style={{
                        flex: 1,
                        padding: 12,
                        borderRadius: 10,
                        border: "1px solid #ddd",
                        background: "white",
                    }}
                >
                    Настроить
                </button>

                <button
                    onClick={() => onRemove(instrument.ticker)}
                    style={{
                        flex: 1,
                        padding: 12,
                        borderRadius: 10,
                        border: "1px solid #ddd",
                        background: "white",
                    }}
                >
                    Удалить
                </button>
            </div>
        </div>
    )
}
