import { useEffect, useState } from "react"
import {
    calculateStartPlan,
    getDashboard,
    getInstruments,
    getSessions,
    startSandbox,
} from "./api"
import { AddInstrumentForm } from "./components/AddInstrumentForm"
import { DashboardCard } from "./components/DashboardCard"
import { InstrumentCard } from "./components/InstrumentCard"
import { SessionsCard } from "./components/SessionsCard"
import { StartPlanCard } from "./components/StartPlanCard"
import type {
    ActiveSession,
    Dashboard,
    Instrument,
    StartPlan,
} from "./types"

export default function App() {
    const [dashboard, setDashboard] =
        useState<Dashboard | null>(null)

    const [instruments, setInstruments] =
        useState<Instrument[]>([])

    const [startPlan, setStartPlan] =
        useState<StartPlan | null>(null)

    const [sessions, setSessions] =
        useState<ActiveSession[]>([])

    const [isAdding, setIsAdding] = useState(false)
    const [newTicker, setNewTicker] = useState("")
    const [newLevels, setNewLevels] = useState(20)
    const [newBaseQuantity, setNewBaseQuantity] = useState("1")

    const [editingTicker, setEditingTicker] =
        useState<string | null>(null)
    const [editLevels, setEditLevels] = useState(20)
    const [editQuantity, setEditQuantity] = useState("1")

    useEffect(() => {
        refreshDashboard()
        refreshSessions()

        getInstruments().then(data => {
            setInstruments(
                data.instruments.map((instrument: Instrument) => ({
                    ...instrument,
                    quantity: 1,
                }))
            )
        })
    }, [])

    function refreshDashboard() {
        getDashboard().then(setDashboard)
    }

    function refreshSessions() {
        getSessions().then(data => {
            setSessions(data.sessions)
        })
    }

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
                quantity: Math.max(1, Number(newBaseQuantity || "1")),
                price: 0,
                required_capital: 0,
            },
        ])

        setNewTicker("")
        setNewLevels(20)
        setNewBaseQuantity("1")
        setIsAdding(false)
        setStartPlan(null)
    }

    function removeInstrument(ticker: string) {
        setInstruments(
            instruments.filter(
                instrument => instrument.ticker !== ticker
            )
        )
        setStartPlan(null)
    }

    function startEdit(instrument: Instrument) {
        setEditingTicker(instrument.ticker)
        setEditLevels(instrument.levels)
        setEditQuantity(String(instrument.quantity ?? 1))
    }

    function saveEdit() {
        if (!editingTicker) {
            return
        }

        setInstruments(
            instruments.map(instrument =>
                instrument.ticker === editingTicker
                    ? {
                        ...instrument,
                        levels: editLevels,
                        quantity: Math.max(
                            1,
                            Number(editQuantity || "1")
                        ),
                    }
                    : instrument
            )
        )

        setEditingTicker(null)
        setStartPlan(null)
    }

    function calculatePlan() {
        calculateStartPlan(
            instruments.map(instrument => ({
                ticker: instrument.ticker,
                levels: instrument.levels,
                quantity: instrument.quantity ?? 1,
            }))
        ).then(setStartPlan)
    }

    function startStrategy() {
        if (!startPlan) {
            return
        }

        startSandbox(
            !startPlan.can_start,
            startPlan.instruments.map(instrument => ({
                ticker: instrument.ticker,
                levels: instrument.levels,
                quantity: instrument.quantity,
            }))
        ).then(() => {
            refreshDashboard()
            refreshSessions()
        })
    }

    if (!dashboard) {
        return <div style={{ padding: 20 }}>Загрузка...</div>
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
            <div style={{ maxWidth: 520, margin: "0 auto" }}>
                <h1>T-Invest Bot</h1>

                <DashboardCard dashboard={dashboard} />

                <SessionsCard sessions={sessions} />

                <div
                    style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        marginTop: 16,
                        marginBottom: 12,
                    }}
                >
                    <h2 style={{ margin: 0 }}>Инструменты</h2>

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
                    <AddInstrumentForm
                        newTicker={newTicker}
                        newLevels={newLevels}
                        newBaseQuantity={newBaseQuantity}
                        onTickerChange={setNewTicker}
                        onLevelsChange={setNewLevels}
                        onBaseQuantityChange={setNewBaseQuantity}
                        onSave={addInstrument}
                        onCancel={() => setIsAdding(false)}
                    />
                )}

                {instruments.map(instrument => (
                    <InstrumentCard
                        key={instrument.ticker}
                        instrument={instrument}
                        isEditing={editingTicker === instrument.ticker}
                        editLevels={editLevels}
                        editQuantity={editQuantity}
                        onStartEdit={startEdit}
                        onRemove={removeInstrument}
                        onEditLevelsChange={setEditLevels}
                        onEditQuantityChange={setEditQuantity}
                        onSaveEdit={saveEdit}
                        onCancelEdit={() => setEditingTicker(null)}
                    />
                ))}

                <button
                    onClick={calculatePlan}
                    style={{
                        width: "100%",
                        padding: 16,
                        marginTop: 12,
                        fontSize: 18,
                        borderRadius: 14,
                        border: "none",
                        background: "#2563eb",
                        color: "white",
                    }}
                >
                    Рассчитать капитал
                </button>

                {startPlan && (
                    <StartPlanCard
                        startPlan={startPlan}
                        onStart={startStrategy}
                    />
                )}
            </div>
        </div>
    )
}
