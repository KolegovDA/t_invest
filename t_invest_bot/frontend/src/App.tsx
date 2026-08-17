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
    startLive,
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

    const [startError, setStartError] =
        useState<string | null>(null)

    const [isStarting, setIsStarting] =
        useState(false)

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


    const tradingMode =
        liveStatus?.trading_mode === "live"
            ? "live"
            : "sandbox"

    const liveTradingEnabled =
        liveStatus?.live_trading_enabled === true


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
        setStartError(null)

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
        setStartError(null)
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
        setStartError(null)

        setModal(null)
    }


    function openStartModal() {
        setStartPlan(null)
        setStartResult(null)
        setStartError(null)

        setModal(
            "start-strategy"
        )
    }


    function calculatePlan() {
        setStartError(null)

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
        )
            .then(plan => {
                setStartPlan(plan)
                setStartResult(null)
                refreshApiUsage()
            })
            .catch(error => {
                setStartError(
                    error instanceof Error
                        ? error.message
                        : String(error)
                )
            })
    }


    async function startStrategy() {
        if (!startPlan) {
            return
        }

        if (
            tradingMode === "live"
            && !liveTradingEnabled
        ) {
            setStartError(
                "Live trading отключен. " +
                "LIVE_TRADING_ENABLED=0"
            )

            return
        }

        const force =
            !startPlan.can_start

        const startInstruments =
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

        setIsStarting(true)
        setStartError(null)
        setStartResult(null)

        try {
            const result =
                tradingMode === "live"
                    ? await startLive(
                        force,
                        startInstruments
                    )
                    : await startSandbox(
                        force,
                        startInstruments
                    )

            setStartResult(
                result
            )

            refreshAll()
            refreshLiveStatus()

            const started =
                tradingMode === "live"
                    ? (
                        result.status ===
                        "started"
                    )
                    : (
                        result.real_sandbox_status ===
                        "started"
                        || result.status ===
                        "started"
                    )

            if (started) {
                window.setTimeout(
                    () => {
                        setModal(null)

                        setActiveTab(
                            "sessions"
                        )
                    },
                    1200
                )
            }

        } catch (error) {
            console.error(
                "Strategy start error:",
                error
            )

            setStartError(
                error instanceof Error
                    ? error.message
                    : String(error)
            )
        } finally {
            setIsStarting(false)
        }
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
                            tradingMode={
                                tradingMode
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
                                    text={
                                        tradingMode ===
                                            "live"
                                            ? "Запусти торговлю на боевом счёте"
                                            : "Запусти первую стратегию"
                                    }
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
                                {tradingMode ===
                                    "live"
                                    ? "Запустить торговлю"
                                    : "Запустить Sandbox"}
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
                            subtitle="ESM Invest System v1.0.2"
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
                        title={
                            tradingMode === "live"
                                ? "Запуск торговли"
                                : "Запуск стратегии"
                        }
                        onClose={() =>
                            setModal(null)
                        }
                    >
                        <div
                            style={
                                modeCardStyle
                            }
                        >
                            <span
                                style={{
                                    color:
                                        "#6b7280",
                                }}
                            >
                                Режим
                            </span>

                            <b
                                style={{
                                    color:
                                        tradingMode ===
                                            "live"
                                            ? "#dc2626"
                                            : "#2563eb",
                                }}
                            >
                                {tradingMode ===
                                    "live"
                                    ? "Боевой счёт"
                                    : "Sandbox"}
                            </b>
                        </div>

                        {tradingMode === "live" &&
                            liveStatus && (
                                <div
                                    style={{
                                        ...modeCardStyle,
                                        marginTop: 8,
                                    }}
                                >
                                    <span
                                        style={{
                                            color:
                                                "#6b7280",
                                        }}
                                    >
                                        Счёт
                                    </span>

                                    <b>
                                        {liveStatus
                                            .selected_account_id ??
                                            "Не выбран"}
                                    </b>
                                </div>
                            )}

                        {tradingMode === "live" &&
                            !liveTradingEnabled && (
                                <div
                                    style={
                                        warningStyle
                                    }
                                >
                                    Live execution
                                    отключен в
                                    конфигурации.
                                </div>
                            )}

                        {startError && (
                            <div
                                style={
                                    errorStyle
                                }
                            >
                                {startError}
                            </div>
                        )}

                        {!startPlan ? (
                            <div
                                style={{
                                    background:
                                        "white",
                                    borderRadius: 18,
                                    padding: 16,
                                    marginTop: 12,
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
                                    Рассчитать капитал
                                </button>
                            </div>
                        ) : (
                            <>
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

                                {tradingMode === "live" &&
                                    !liveTradingEnabled && (
                                        <div
                                            style={{
                                                color:
                                                    "#dc2626",
                                                fontSize: 13,
                                                marginTop: 8,
                                            }}
                                        >
                                            Запуск будет
                                            заблокирован до
                                            LIVE_TRADING_ENABLED=1.
                                        </div>
                                    )}

                                {isStarting && (
                                    <div
                                        style={{
                                            marginTop: 10,
                                            textAlign:
                                                "center",
                                            color:
                                                "#6b7280",
                                        }}
                                    >
                                        Запуск...
                                    </div>
                                )}
                            </>
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
                ESM Invest System
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
    tradingMode,
    onStart,
    onSessions,
}: {
    sessionsCount: number
    tradingMode: "sandbox" | "live"
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
                {tradingMode === "live"
                    ? "+ Торговать"
                    : "+ Запустить"}
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
                value="1.0.2 MVP"
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


const modeCardStyle = {
    background: "white",
    borderRadius: 14,
    padding: 13,
    display: "flex",
    justifyContent: "space-between",
    gap: 12,
}


const warningStyle = {
    marginTop: 10,
    padding: 12,
    borderRadius: 12,
    background: "#fff7ed",
    color: "#9a3412",
    fontSize: 14,
}


const errorStyle = {
    marginTop: 10,
    padding: 12,
    borderRadius: 12,
    background: "#fee2e2",
    color: "#991b1b",
    fontSize: 14,
    wordBreak: "break-word" as const,
}
