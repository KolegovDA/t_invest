import { useEffect, useState } from "react"
import { getDashboard, getInstruments } from "./api"

type Dashboard = {
    accounts: number
    capital: number
    active_positions: number
    profit: number
    instruments: string[]
}

type Instrument = {
    ticker: string
    levels: number
    price: number
    required_capital: number
}

export default function App() {
    const [dashboard, setDashboard] =
        useState<Dashboard | null>(null)

    const [instruments, setInstruments] =
        useState<Instrument[]>([])

    const [isAdding, setIsAdding] =
        useState(false)

    const [newTicker, setNewTicker] =
        useState("")

    const [newLevels, setNewLevels] =
        useState(20)

    const [newBaseQuantity, setNewBaseQuantity] =
        useState(1)

    useEffect(() => {
        getDashboard().then(setDashboard)

        getInstruments().then(data => {
            setInstruments(data.instruments)
        })
    }, [])

    function addInstrument() {
        const ticker = newTicker.trim().toUpperCase()

        if (!ticker) {
            return
        }

        setInstruments([
            ...instruments,
            {
                ticker,
                levels: newLevels,
                price: 0,
                required_capital: 0,
            },
        ])

        setNewTicker("")
        setNewLevels(20)
        setNewBaseQuantity(1)
        setIsAdding(false)
    }

    function removeInstrument(
        ticker: string,
    ) {
        setInstruments(
            instruments.filter(
                instrument => instrument.ticker !== ticker
            )
        )
    }

    if (!dashboard) {
        return (
            <div style={{ padding: 20 }}>
                Загрузка...
            </div>
        )
    }

    return (
        <div
            style={{
                minHeight: "100vh",
                background: "#f4f6f8",
                padding: 16,
                fontFamily: "Arial",
            }}
        >
            <div
                style={{
                    maxWidth: 520,
                    margin: "0 auto",
                }}
            >
                <h1>T-Invest Bot</h1>

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
                    <p>
                        Капитал:{" "}
                        {dashboard.capital.toLocaleString()} ₽
                    </p>
                    <p>
                        Активных позиций:{" "}
                        {dashboard.active_positions}
                    </p>
                    <p>Прибыль: {dashboard.profit} ₽</p>
                </div>

                <div
                    style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        marginBottom: 12,
                    }}
                >
                    <h2 style={{ margin: 0 }}>
                        Инструменты
                    </h2>

                    <button
                        onClick={() => setIsAdding(true)}
                        style={{
                            padding: "10px 14px",
                            borderRadius: 10,
                            border: "none",
                            background: "#111827",
                            color: "white",
                        }}
                    >
                        + Добавить
                    </button>
                </div>

                {isAdding && (
                    <div
                        style={{
                            background: "white",
                            borderRadius: 16,
                            padding: 16,
                            marginBottom: 12,
                            boxShadow: "0 6px 16px rgba(0,0,0,0.06)",
                        }}
                    >
                        <h3 style={{ marginTop: 0 }}>
                            Новый инструмент
                        </h3>

                        <label>
                            Тикер
                        </label>

                        <input
                            value={newTicker}
                            onChange={event =>
                                setNewTicker(event.target.value)
                            }
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
                            {[10, 20, 30].map(level => (
                                <button
                                    key={level}
                                    onClick={() =>
                                        setNewLevels(level)
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
                            ))}
                        </div>

                        <label>
                            Базовый лот
                        </label>

                        <input
                            type="number"
                            min={1}
                            value={newBaseQuantity}
                            onChange={event =>
                                setNewBaseQuantity(
                                    Number(event.target.value)
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
                            }}
                        >
                            <button
                                onClick={addInstrument}
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
                                onClick={() => setIsAdding(false)}
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

                {instruments.map(instrument => (
                    <div
                        key={instrument.ticker}
                        style={{
                            background: "white",
                            borderRadius: 16,
                            padding: 16,
                            marginBottom: 12,
                            boxShadow: "0 6px 16px rgba(0,0,0,0.06)",
                        }}
                    >
                        <h3 style={{ marginTop: 0 }}>
                            {instrument.ticker}
                        </h3>

                        <p>
                            Уровней: {instrument.levels}
                        </p>

                        <p>
                            Текущая цена:{" "}
                            {instrument.price.toLocaleString()} ₽
                        </p>

                        <p>
                            Требуется капитал:{" "}
                            {instrument.required_capital.toLocaleString()} ₽
                        </p>

                        <div
                            style={{
                                display: "flex",
                                gap: 8,
                            }}
                        >
                            <button
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
                                onClick={() =>
                                    removeInstrument(
                                        instrument.ticker
                                    )
                                }
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
                ))}

                <button
                    style={{
                        width: "100%",
                        padding: 16,
                        marginTop: 12,
                        fontSize: 18,
                        borderRadius: 14,
                        border: "none",
                        background: "#16a34a",
                        color: "white",
                    }}
                >
                    Запустить стратегию
                </button>
            </div>
        </div>
    )
}
