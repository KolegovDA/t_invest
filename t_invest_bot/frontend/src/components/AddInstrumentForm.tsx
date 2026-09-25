import type {
    InstrumentSearchResult,
} from "../types"


type Props = {
    newTicker: string
    newLevels: number
    newBaseQuantity: string

    searchResults:
        InstrumentSearchResult[]

    isSearching: boolean

    onTickerChange:
        (value: string) => void

    onSearch:
        (value: string) => void

    onSelect:
        (item: InstrumentSearchResult) => void

    onLevelsChange:
        (value: number) => void

    onBaseQuantityChange:
        (value: string) => void

    onSave: () => void
    onCancel: () => void
}


export function AddInstrumentForm({
    newTicker,
    newLevels,
    newBaseQuantity,
    searchResults,
    isSearching,
    onTickerChange,
    onSearch,
    onSelect,
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
                boxShadow:
                    "0 6px 16px rgba(0,0,0,0.06)",
            }}
        >
            <h3
                style={{
                    marginTop: 0,
                }}
            >
                Новый инструмент
            </h3>

            <label>
                Поиск акции
            </label>

            <input
                value={newTicker}
                onChange={event => {
                    const value =
                        event.target.value

                    onTickerChange(
                        value
                    )

                    onSearch(
                        value
                    )
                }}
                placeholder="Тикер или название, например SBER или Сбербанк"
                style={{
                    width: "100%",
                    padding: 12,
                    marginTop: 6,
                    marginBottom: 8,
                    borderRadius: 10,
                    border:
                        "1px solid #ddd",
                    boxSizing:
                        "border-box",
                    fontSize: 16,
                }}
            />

            {isSearching && (
                <div
                    style={{
                        color:
                            "#6b7280",
                        fontSize: 13,
                        marginBottom: 8,
                    }}
                >
                    Поиск инструментов...
                </div>
            )}

            {!isSearching
                && newTicker.trim()
                && searchResults.length === 0
                && (
                    <div
                        style={{
                            color:
                                "#6b7280",
                            fontSize: 13,
                            marginBottom: 8,
                        }}
                    >
                        Совпадения не найдены.
                        Можно ввести точный тикер вручную.
                    </div>
                )}

            {searchResults.length > 0 && (
                <div
                    style={{
                        maxHeight: 250,
                        overflowY:
                            "auto",
                        border:
                            "1px solid #e5e7eb",
                        borderRadius: 10,
                        marginBottom: 14,
                    }}
                >
                    {searchResults.map(
                        item => (
                            <button
                                key={
                                    item.instrument_uid
                                }
                                type="button"
                                onClick={() =>
                                    onSelect(
                                        item
                                    )
                                }
                                style={{
                                    width:
                                        "100%",
                                    border:
                                        "none",
                                    borderBottom:
                                        "1px solid #f3f4f6",
                                    background:
                                        "white",
                                    padding:
                                        "11px 12px",
                                    textAlign:
                                        "left",
                                    cursor:
                                        "pointer",
                                }}
                            >
                                <div
                                    style={{
                                        display:
                                            "flex",
                                        justifyContent:
                                            "space-between",
                                        gap: 10,
                                    }}
                                >
                                    <b>
                                        {
                                            item.ticker
                                        }
                                    </b>

                                    <span
                                        style={{
                                            color:
                                                "#6b7280",
                                            fontSize: 12,
                                        }}
                                    >
                                        Лот: {
                                            item.lot_size
                                        }
                                    </span>
                                </div>

                                <div
                                    style={{
                                        marginTop: 3,
                                        color:
                                            "#4b5563",
                                        fontSize: 13,
                                    }}
                                >
                                    {
                                        item.name
                                    }
                                    {" · "}
                                    {
                                        item.currency
                                            .toUpperCase()
                                    }
                                </div>
                            </button>
                        )
                    )}
                </div>
            )}

            <label>
                Количество уровней
            </label>

            <div
                style={{
                    display: "flex",
                    gap: 8,
                    marginTop: 8,
                    marginBottom: 12,
                }}
            >
                {[10, 20, 30].map(
                    level => (
                        <button
                            key={level}
                            type="button"
                            onClick={() =>
                                onLevelsChange(
                                    level
                                )
                            }
                            style={{
                                flex: 1,
                                padding: 12,
                                borderRadius: 10,
                                border:
                                    newLevels === level
                                        ? "2px solid #111827"
                                        : "1px solid #ddd",
                                background:
                                    newLevels === level
                                        ? "#eef2ff"
                                        : "white",
                            }}
                        >
                            {level}
                        </button>
                    )
                )}
            </div>

            <label>
                Базовый лот
            </label>

            <input
                type="text"
                inputMode="numeric"
                value={newBaseQuantity}
                onChange={event =>
                    onBaseQuantityChange(
                        event.target.value
                            .replace(
                                /\D/g,
                                ""
                            )
                    )
                }
                style={{
                    width: "100%",
                    padding: 12,
                    marginTop: 6,
                    marginBottom: 12,
                    borderRadius: 10,
                    border:
                        "1px solid #ddd",
                    boxSizing:
                        "border-box",
                    fontSize: 16,
                }}
            />

            <div
                style={{
                    display: "flex",
                    gap: 8,
                }}
            >
                <button
                    type="button"
                    onClick={onSave}
                    disabled={
                        !newTicker.trim()
                    }
                    style={{
                        flex: 1,
                        padding: 12,
                        borderRadius: 10,
                        border: "none",
                        background:
                            "#16a34a",
                        color: "white",
                        opacity:
                            newTicker.trim()
                                ? 1
                                : 0.5,
                    }}
                >
                    Сохранить
                </button>

                <button
                    type="button"
                    onClick={onCancel}
                    style={{
                        flex: 1,
                        padding: 12,
                        borderRadius: 10,
                        border:
                            "1px solid #ddd",
                        background:
                            "white",
                    }}
                >
                    Отмена
                </button>
            </div>
        </div>
    )
}
