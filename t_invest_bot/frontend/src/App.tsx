import { useEffect, useState } from "react"

import {
    calculateStartPlan,
    getApiUsage,
    getDashboard,
    getInstruments,
    getLiveStatus,
    getRunnerStatus,
    getSession,
    getSessions,
    startSandbox,
    stopSession,
} from "./api"

import { AddInstrumentForm } from "./components/AddInstrumentForm"
import { ApiUsageCard } from "./components/ApiUsageCard"
import { AppModal } from "./components/AppModal"
import {
    AppTab,
    BottomNavigation,
} from "./components/BottomNavigation"
import { DashboardCard } from "./components/DashboardCard"
import { InstrumentCard } from "./components/InstrumentCard"
import { InstrumentSettingsForm } from "./components/InstrumentSettingsForm"
import { LiveStatusCard } from "./components/LiveStatusCard"
import { RunnerStatusCard } from "./components/RunnerStatusCard"
import { SessionDetailCard } from "./components/SessionDetailCard"
import { SessionsCard } from "./components/SessionsCard"
import { StartPlanCard } from "./components/StartPlanCard"

import type {
    ActiveSession,
    ApiUsage,
    Dashboard,
    Instrument,
    LiveStatus,
    RunnerStatus,
    StartPlan,
    StartSandboxResult,
} from "./types"


type ModalType =
    | "add-instrument"
    | "edit-instrument"
    | "start-strategy"
    | "session-detail"
    | null


export default function App() {
    const [activeTab, setActiveTab] =
        useState<AppTab>("home")

    const [modal, setModal] =
        useState<ModalType>(null)

    const [dashboard, setDashboard] =
        useState<Dashboard | null>(null)

    const [apiUsage, setApiUsage] =
        useState<ApiUsage | null>(null)

    const [runners, setRunners] =
        useState<RunnerStatus[]>([])

    const [liveStatus, setLiveStatus] =
        useState<LiveStatus | null>(null)

    const [instruments, setInstruments] =
        useState<Instrument[]>([])

    const [sessions, setSessions] =
        useState<ActiveSession[]>([])

    const [
        selectedSession,
        setSelectedSession,
    ] = useState<ActiveSession | null>(null)

    const [startPlan, setStartPlan] =
        useState<StartPlan | null>(null)

    const [
        startResult,
        setStartResult,
    ] = useState<StartSandboxResult | null>(
        null
    )

    const [newTicker, setNewTicker] =
        useState("")

    const [newLevels, setNewLevels] =
        useState(20)

    const [
        newBaseQuantity,
        setNewBaseQuantity,
    ] = useState("1")

    const [
        editingTicker,
        setEditingTicker,
    ] = useState<string | null>(null)

    const [editLevels, setEditLevels] =
        useState(20)

    const [
        editQuantity,
        setEditQuantity,
    ] = useState("1")


    useEffect(() => {
        refreshAll()
        refreshLiveStatus()

        getInstruments().then(data => {
            setInstruments(
                data.instruments.map(
                    (instrument: Instrument) => ({
                        ...instrument,
                        quantity:
                            instrument.quantity ??
                            1,
                    })
                )
            )
        })

        const intervalId =
            window.setInterval(
                refreshAll,
                5000
            )

        return () =>
            window.clearInterval(intervalId)
    }, [])


    function refreshAll() {
        refreshDashboard()
        refreshSessions()
        refreshApiUsage()
        refreshRunnerStatus()
    }


    function refreshDashboard() {
        getDashboard().then(setDashboard)
    }


    function refreshSessions() {
        getSessions().then(data => {
            setSessions(data.sessions)
        })
    }


    function refreshApiUsage() {
        getApiUsage().then(setApiUsage)
    }


    function refreshRunnerStatus() {
        getRunnerStatus().then(data => {
            setRunners(data.runners)
        })
    }


    function refreshLiveStatus() {
        getLiveStatus()
            .then(setLiveStatus)
            .catch(error => {
                console.error(
                    "Live status error:",
                    error
                )
            })
    }


    function addInstrument() {
        const ticker =
            newTicker.trim().toUpperCase()

        if (!ticker) {
            return
        }

        setInstruments(current => [
            ...current,
            {
                ticker,
                levels: newLevels,
                quantity: Math.max(
                    1,
                    Number(
                        newBaseQuantity || "1"
                    )
                ),
                price: 0,
                required_capital: 0,
            },
        ])

        setNewTicker("")
        setNewLevels(20)
        setNewBaseQuantity("1")
        setStartPlan(null)
        setStartResult(null)
        setModal(null)
    }


    function removeInstrument(
        ticker: string
    ) {
        setInstruments(current =>
            current.filter(
                instrument =>
                    instrument.ticker !== ticker
            )
        )

        setStartPlan(null)
        setStartResult(null)
    }


    function openInstrumentSettings(
        instrument: Instrument
    ) {
        setEditingTicker(
            instrument.ticker
        )

        setEditLevels(
            instrument.levels
        )

        setEditQuantity(
            String(
                instrument.quantity ?? 1
            )
        )

        setModal("edit-instrument")
    }


    function saveInstrumentSettings() {
        if (!editingTicker) {
            return
        }

        setInstruments(current =>
            current.map(instrument =>
                instrument.ticker ===
                    editingTicker
                    ? {
                        ...instrument,
                        levels:
                            editLevels,
                        quantity:
                            Math.max(
                                1,
                                Number(
                                    editQuantity ||
                                    "1"
                                )
                            ),
                    }
                    : instrument
            )
        )

        setStartPlan(null)
        setStartResult(null)
        setModal(null)
    }


    function openStartModal() {
        setStartPlan(null)
        setStartResult(null)

        setModal(
            "start-strategy"
        )
    }


    function calculatePlan() {
        calculateStartPlan(
            instruments.map(
                instrument => ({
                    ticker:
                        instrument.ticker,
                    levels:
                        instrument.levels,
                    quantity:
                        instrument.quantity ??
                        1,
                })
            )
        ).then(plan => {
            setStartPlan(plan)
            setStartResult(null)
            refreshApiUsage()
        })
    }


    function startStrategy() {
        if (!startPlan) {
            return
        }

        startSandbox(
            !startPlan.can_start,
            startPlan.instruments.map(
                instrument => ({
                    ticker:
                        instrument.ticker,
                    levels:
                        instrument.levels,
                    quantity:
                        instrument.quantity,
                })
            )
        ).then(result => {
            setStartResult(result)

            refreshAll()

            if (
                result.real_sandbox_status ===
                "started"
            ) {
                setTimeout(() => {
                    setModal(null)
                    setActiveTab(
                        "sessions"
                    )
                }, 1200)
            }
        })
    }


    function openSession(
        ticker: string
    ) {
        getSession(ticker).then(
            session => {
                setSelectedSession(
                    session
                )

                setModal(
                    "session-detail"
                )
            }
        )
    }


    function stopSelectedSession(
        ticker: string
    ) {
        stopSession(ticker).then(
            result => {
                if (result.removed) {
                    setSelectedSession(
                        null
                    )

                    setModal(null)
                } else {
                    setSelectedSession(
                        result
                    )
                }

                refreshAll()
            }
        )
    }


    if (!dashboard) {
        return (
            <div
                style={{
                    padding: 20,
                    fontFamily:
                        "Arial, sans-serif",
                }}
            >
                Загрузка...
            </div>
        )
    }


    return (
        <div
            style={{
                minHeight: "100vh",
                background: "#f4f6f8",
                fontFamily:
                    "-apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif",
            }}
        >
            <div
                style={{
                    maxWidth: 560,
                    margin: "0 auto",
                    padding:
                        "18px 16px 105px",
                }}
            >
                <Header />

                {activeTab === "home" && (
                    <>
                        <DashboardCard
                            dashboard={
                                dashboard
                            }
                        />

                        <QuickActions
                            sessionsCount={
                                sessions.length
                            }
                            onStart={
                                openStartModal
                            }
                            onSessions={() =>
                                setActiveTab(
                                    "sessions"
                                )
                            }
                        />

                        <RunnerStatusCard
                            runners={
                                runners
                            }
                        />
                    </>
                )}

                {activeTab ===
                    "sessions" && (
                        <>
                            <SectionTitle
                                title="Сессии"
                                subtitle={`${sessions.length} активных`}
                            />

                            {sessions.length > 0 ? (
                                <SessionsCard
                                    sessions={
                                        sessions
                                    }
                                    onOpen={
                                        openSession
                                    }
                                />
                            ) : (
                                <EmptyState
                                    title="Нет активных сессий"
                                    text="Запусти первую стратегию"
                                    button="Запустить"
                                    onClick={
                                        openStartModal
                                    }
                                />
                            )}
                        </>
                    )}

                {activeTab ===
                    "instruments" && (
                        <>
                            <SectionTitle
                                title="Инструменты"
                                subtitle={`${instruments.length} выбрано`}
                                action={
                                    <button
                                        onClick={() =>
                                            setModal(
                                                "add-instrument"
                                            )
                                        }
                                        style={
                                            smallPrimaryButton
                                        }
                                    >
                                        + Добавить
                                    </button>
                                }
                            />

                            {instruments.map(
                                instrument => (
                                    <InstrumentCard
                                        key={
                                            instrument.ticker
                                        }
                                        instrument={
                                            instrument
                                        }
                                        onConfigure={
                                            openInstrumentSettings
                                        }
                                        onRemove={
                                            removeInstrument
                                        }
                                    />
                                )
                            )}

                            <button
                                onClick={
                                    openStartModal
                                }
                                disabled={
                                    instruments.length ===
                                    0
                                }
                                style={{
                                    ...primaryButton,
                                    opacity:
                                        instruments.length ===
                                            0
                                            ? 0.5
                                            : 1,
                                }}
                            >
                                Запустить стратегию
                            </button>
                        </>
                    )}

                {activeTab === "api" && (
                    <>
                        <SectionTitle
                            title="API и Runner"
                            subtitle="Монитор нагрузки"
                        />

                        <ApiUsageCard
                            apiUsage={
                                apiUsage
                            }
                        />

                        <RunnerStatusCard
                            runners={
                                runners
                            }
                        />
                    </>
                )}

                {activeTab ===
                    "settings" && (
                        <>
                            <SectionTitle
                                title="Настройки"
                                subtitle="T-Invest Bot v1.0"
                            />

                            <LiveStatusCard
                                status={
                                    liveStatus
                                }
                            />

                            <button
                                onClick={
                                    refreshLiveStatus
                                }
                                style={{
                                    ...primaryButton,
                                    marginBottom: 16,
                                }}
                            >
                                Обновить боевой счёт
                            </button>

                            <SettingsCard
                                realSandbox={
                                    runners.some(
                                        runner =>
                                            runner.is_running
                                    )
                                }
                                liveStatus={
                                    liveStatus
                                }
                            />
                        </>
                    )}
            </div>

            <BottomNavigation
                activeTab={activeTab}
                onChange={setActiveTab}
            />

            {modal ===
                "add-instrument" && (
                    <AppModal
                        title="Добавить инструмент"
                        onClose={() =>
                            setModal(null)
                        }
                    >
                        <AddInstrumentForm
                            newTicker={
                                newTicker
                            }
                            newLevels={
                                newLevels
                            }
                            newBaseQuantity={
                                newBaseQuantity
                            }
                            onTickerChange={
                                setNewTicker
                            }
                            onLevelsChange={
                                setNewLevels
                            }
                            onBaseQuantityChange={
                                setNewBaseQuantity
                            }
                            onSave={
                                addInstrument
                            }
                            onCancel={() =>
                                setModal(null)
                            }
                        />
                    </AppModal>
                )}

            {modal ===
                "edit-instrument" &&
                editingTicker && (
                    <AppModal
                        title="Настройка инструмента"
                        onClose={() =>
                            setModal(null)
                        }
                    >
                        <InstrumentSettingsForm
                            ticker={
                                editingTicker
                            }
                            levels={
                                editLevels
                            }
                            quantity={
                                editQuantity
                            }
                            onLevelsChange={
                                setEditLevels
                            }
                            onQuantityChange={
                                setEditQuantity
                            }
                            onSave={
                                saveInstrumentSettings
                            }
                        />
                    </AppModal>
                )}

            {modal ===
                "start-strategy" && (
                    <AppModal
                        title="Запуск стратегии"
                        onClose={() =>
                            setModal(null)
                        }
                    >
                        {!startPlan ? (
                            <div
                                style={{
                                    background:
                                        "white",
                                    borderRadius: 18,
                                    padding: 16,
                                }}
                            >
                                <p>
                                    Инструментов:{" "}
                                    <b>
                                        {
                                            instruments.length
                                        }
                                    </b>
                                </p>

                                <p
                                    style={{
                                        color:
                                            "#6b7280",
                                    }}
                                >
                                    Перед запуском
                                    рассчитаем
                                    необходимый
                                    капитал.
                                </p>

                                <button
                                    onClick={
                                        calculatePlan
                                    }
                                    style={
                                        primaryButton
                                    }
                                >
                                    Рассчитать капитал
                                </button>
                            </div>
                        ) : (
                            <StartPlanCard
                                startPlan={
                                    startPlan
                                }
                                startResult={
                                    startResult
                                }
                                onStart={
                                    startStrategy
                                }
                            />
                        )}
                    </AppModal>
                )}

            {modal ===
                "session-detail" &&
                selectedSession && (
                    <AppModal
                        title={
                            selectedSession.ticker
                        }
                        onClose={() =>
                            setModal(null)
                        }
                    >
                        <SessionDetailCard
                            session={
                                selectedSession
                            }
                            onClose={() =>
                                setModal(null)
                            }
                            onStop={
                                stopSelectedSession
                            }
                        />
                    </AppModal>
                )}
        </div>
    )
}


function Header() {
    return (
        <div
            style={{
                marginBottom: 20,
            }}
        >
            <div
                style={{
                    color: "#6b7280",
                    fontSize: 13,
                    fontWeight: 600,
                }}
            >
                T-INVEST BOT
            </div>

            <h1
                style={{
                    margin: "3px 0 0",
                    fontSize: 29,
                }}
            >
                Портфель
            </h1>
        </div>
    )
}


function SectionTitle({
    title,
    subtitle,
    action,
}: {
    title: string
    subtitle?: string
    action?: React.ReactNode
}) {
    return (
        <div
            style={{
                display: "flex",
                alignItems: "center",
                justifyContent:
                    "space-between",
                marginBottom: 16,
            }}
        >
            <div>
                <h2
                    style={{
                        margin: 0,
                        fontSize: 25,
                    }}
                >
                    {title}
                </h2>

                {subtitle && (
                    <div
                        style={{
                            color: "#6b7280",
                            marginTop: 3,
                        }}
                    >
                        {subtitle}
                    </div>
                )}
            </div>

            {action}
        </div>
    )
}


function QuickActions({
    sessionsCount,
    onStart,
    onSessions,
}: {
    sessionsCount: number
    onStart: () => void
    onSessions: () => void
}) {
    return (
        <div
            style={{
                display: "grid",
                gridTemplateColumns:
                    "1fr 1fr",
                gap: 10,
                marginBottom: 16,
            }}
        >
            <button
                onClick={onStart}
                style={primaryButton}
            >
                + Запустить
            </button>

            <button
                onClick={onSessions}
                style={{
                    ...primaryButton,
                    background: "white",
                    color: "#111827",
                    border:
                        "1px solid #e5e7eb",
                }}
            >
                Сессии ({sessionsCount})
            </button>
        </div>
    )
}


function EmptyState({
    title,
    text,
    button,
    onClick,
}: {
    title: string
    text: string
    button: string
    onClick: () => void
}) {
    return (
        <div
            style={{
                background: "white",
                borderRadius: 18,
                padding: 22,
                textAlign: "center",
            }}
        >
            <h3>{title}</h3>

            <p
                style={{
                    color: "#6b7280",
                }}
            >
                {text}
            </p>

            <button
                onClick={onClick}
                style={primaryButton}
            >
                {button}
            </button>
        </div>
    )
}


function SettingsCard({
    realSandbox,
    liveStatus,
}: {
    realSandbox: boolean
    liveStatus: LiveStatus | null
}) {
    return (
        <div
            style={{
                background: "white",
                borderRadius: 18,
                padding: 16,
            }}
        >
            <SettingRow
                label="Режим"
                value={
                    liveStatus?.trading_mode ??
                    "sandbox"
                }
            />

            <SettingRow
                label="Sandbox Runner"
                value={
                    realSandbox
                        ? "Запущен"
                        : "Остановлен"
                }
            />

            <SettingRow
                label="Live execution"
                value={
                    liveStatus?.live_trading_enabled
                        ? "Включен"
                        : "Отключен"
                }
            />

            <SettingRow
                label="Боевой счёт"
                value={
                    liveStatus?.account_found
                        ? "Подключен"
                        : "Не выбран"
                }
            />

            <SettingRow
                label="Версия"
                value="1.0 MVP"
            />
        </div>
    )
}


function SettingRow({
    label,
    value,
}: {
    label: string
    value: string
}) {
    return (
        <div
            style={{
                display: "flex",
                justifyContent:
                    "space-between",
                padding: "14px 0",
                borderBottom:
                    "1px solid #f3f4f6",
            }}
        >
            <span>{label}</span>

            <b>{value}</b>
        </div>
    )
}


const primaryButton = {
    width: "100%",
    padding: 14,
    borderRadius: 13,
    border: "none",
    background: "#2563eb",
    color: "white",
    fontSize: 16,
    fontWeight: 600,
    cursor: "pointer",
}


const smallPrimaryButton = {
    padding: "10px 13px",
    borderRadius: 11,
    border: "none",
    background: "#2563eb",
    color: "white",
    fontWeight: 600,
    cursor: "pointer",
}
