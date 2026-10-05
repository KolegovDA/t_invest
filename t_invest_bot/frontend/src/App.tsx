import {
    useEffect,
    useState,
} from "react"

import {
    calculateStartPlan,
    drainSession,
    getAccountsOverview,
    getAuthMe,
    getAuthStatus,
    getDashboard,
    getHealth,
    getInstruments,
    getLiveStatus,
    getOperations,
    getSession,
    getSessions,
    resumeSession,
    searchInstruments,
    startLive,
    startSandbox,
    stopSession,
    validateLiveStart,
} from "./api"

import {
    getTradingAccounts,
} from "./accounts/api"

import {
    AccountsPanel,
} from "./accounts/AccountsPanel"

import {
    getDeviceId,
} from "./auth/security"

import {BybitStartForm} from "./components/BybitStartForm"
import {
    AddInstrumentForm,
} from "./components/AddInstrumentForm"

import {
    OverviewAccountsCard,
} from "./components/AccountsOverviewCard"

import {
    AppModal,
} from "./components/AppModal"

import {
    AuthScreen,
} from "./components/AuthScreen"

import {
    AppTab,
    BottomNavigation,
} from "./components/BottomNavigation"

import {
    DashboardCard,
} from "./components/DashboardCard"

import {
    InstrumentCard,
} from "./components/InstrumentCard"

import {
    InstrumentSettingsForm,
} from "./components/InstrumentSettingsForm"

import {
    InstrumentSelectionCard,
} from "./components/InstrumentSelectionCard"

import {
    NotificationSettingsCard,
} from "./components/NotificationSettingsCard"

import {
    OperationsHistoryCard,
} from "./components/OperationsHistoryCard"

import {
    PlatformApiCard,
} from "./components/PlatformApiCard"

import {
    SecuritySettingsCard,
} from "./components/SecuritySettingsCard"

import {
    SessionChartCard,
} from "./components/SessionChartCard"

import {
    SessionDetailCard,
} from "./components/SessionDetailCard"

import {
    StartPlanCard,
} from "./components/StartPlanCard"

import {
    ThemeToggle,
} from "./components/ThemeToggle"

import {
    TradingOverviewCard,
} from "./components/TradingOverviewCard"

import {
    UserSettingsCard,
} from "./components/UserSettingsCard"

import type {
    AuthUser,
} from "./api"

import type {
    TradingAccount,
} from "./accounts/types"

import type {
    AccountsOverview,
    ActiveSession,
    Dashboard,
    DashboardAccountDetail,
    Instrument,
    InstrumentSearchResult,
    LiveStartValidationResult,
    LiveStatus,
    OperationLogEntry,
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
    const [
        activeTab,
        setActiveTab,
    ] = useState<AppTab>(
        "home"
    )

    const [
        modal,
        setModal,
    ] = useState<ModalType>(
        null
    )

    const [
        dashboard,
        setDashboard,
    ] = useState<
        Dashboard | null
    >(null)

    const [
        overview,
        setOverview,
    ] = useState<
        AccountsOverview | null
    >(null)

    const [selectionOpen, setSelectionOpen] = useState(false)
    const [accountsOpen, setAccountsOpen] = useState(false)

    const [
        appVersion,
        setAppVersion,
    ] = useState<
        string | null
    >(null)

    const [
        liveStatus,
        setLiveStatus,
    ] = useState<
        LiveStatus | null
    >(null)

    const [
        operations,
        setOperations,
    ] = useState<
        OperationLogEntry[]
    >([])

    const [
        tradingAccounts,
        setTradingAccounts,
    ] = useState<
        TradingAccount[]
    >([])

    const [
        selectedTradingAccountId,
        setSelectedTradingAccountId,
    ] = useState<
        string | null
    >(null)

    const [
        selectedSandboxAccountId,
        setSelectedSandboxAccountId,
    ] = useState<
        string | null
    >(null)

    const [
        liveValidation,
        setLiveValidation,
    ] = useState<
        LiveStartValidationResult | null
    >(null)

    const [
        isValidating,
        setIsValidating,
    ] = useState(
        false
    )

    const [
        instruments,
        setInstruments,
    ] = useState<
        Instrument[]
    >([])

    const [
        sessions,
        setSessions,
    ] = useState<
        ActiveSession[]
    >([])

    const [
        selectedSession,
        setSelectedSession,
    ] = useState<
        ActiveSession | null
    >(null)

    const [
        startPlan,
        setStartPlan,
    ] = useState<
        StartPlan | null
    >(null)

    const [
        startResult,
        setStartResult,
    ] = useState<
        StartSandboxResult | null
    >(null)

    const [
        startError,
        setStartError,
    ] = useState<
        string | null
    >(null)

    const [
        isStarting,
        setIsStarting,
    ] = useState(
        false
    )

    const [
        newTicker,
        setNewTicker,
    ] = useState(
        ""
    )

    const [
        newLevels,
        setNewLevels,
    ] = useState(
        20
    )

    const [
        newBaseQuantity,
        setNewBaseQuantity,
    ] = useState(
        "1"
    )

    const [
        instrumentSearchResults,
        setInstrumentSearchResults,
    ] = useState<
        InstrumentSearchResult[]
    >([])

    const [
        isSearchingInstruments,
        setIsSearchingInstruments,
    ] = useState(
        false
    )

    const [
        editingTicker,
        setEditingTicker,
    ] = useState<
        string | null
    >(null)

    const [
        editLevels,
        setEditLevels,
    ] = useState(
        20
    )

    const [
        editQuantity,
        setEditQuantity,
    ] = useState(
        "1"
    )

    const deviceId = (
        getDeviceId()
    )

    const [
        authChecked,
        setAuthChecked,
    ] = useState(
        false
    )

    const [
        authUser,
        setAuthUser,
    ] = useState<
        AuthUser | null
    >(null)

    const [
        authMode,
        setAuthMode,
    ] = useState<
        "register"
        | "login"
        | "pin"
    >(
        "login"
    )


    useEffect(() => {
        if (!authUser) return
        const timer = setInterval(() => { getAuthMe().catch(() => {}) }, 30000)
        return () => clearInterval(timer)
    }, [authUser])

    const [startPlatform, setStartPlatform] = useState("")

    const tradingMode: string = "live"


    const enabledLiveAccounts =
        tradingAccounts
            .filter(
                account =>
                    account.enabled
                    && account.mode
                    === "live"
            )


    const enabledSandboxAccounts =
        tradingAccounts
            .filter(
                account =>
                    account.enabled
                    && account.mode
                    === "sandbox"
            )


    useEffect(
        () => {
            let cancelled = false

            getAuthStatus(
                deviceId
            )

                .then(
                    async status => {
                        let user: (
                            AuthUser
                            | null
                        ) = null

                        try {
                            const data = (
                                await getAuthMe()
                            )

                            user = (
                                data
                                    .user
                            )
                        } catch {
                            user = null
                        }

                        if (cancelled) {
                            return
                        }

                        setAuthChecked(
                            true
                        )

                        if (
                            !status
                                .has_users
                        ) {
                            setAuthMode(
                                "register"
                            )

                            return
                        }

                        if (user) {
                            setAuthUser(
                                user
                            )

                            return
                        }

                        setAuthMode(
                            status
                                .device_has_pin
                                ? "pin"
                                : "login"
                        )
                    }
                )

                .catch(
                    () => {
                        if (cancelled) {
                            return
                        }

                        setAuthChecked(
                            true
                        )

                        setAuthMode(
                            "login"
                        )
                    }
                )

            return () => {
                cancelled = true
            }
        },

        [deviceId]
    )

    useEffect(
        () => {
            refreshAll()

            refreshLiveStatus()

            refreshTradingAccounts()

            getHealth()
                .then(
                    health => {
                        setAppVersion(
                            health.version
                            ?? null
                        )
                    }
                )

                .catch(
                    () => {
                        setAppVersion(
                            null
                        )
                    }
                )

            getInstruments()
                .then(
                    data => {
                        setInstruments(
                            data
                                .instruments
                                .map(
                                    (
                                        instrument:
                                            Instrument
                                    ) => ({
                                        ...instrument,

                                        quantity:
                                            instrument
                                                .quantity
                                            ?? 1,
                                    })
                                )
                        )
                    }
                )

            const intervalId =
                window.setInterval(
                    refreshAll,
                    15000
                )

            return () =>
                window
                    .clearInterval(
                        intervalId
                    )
        },
        [authUser]
    )


    function refreshAll() {
        refreshDashboard()
        refreshSessions()
        refreshOverview()
        refreshOperations()
    }

    function refreshOperations() {
        getOperations()
            .then(
                data => {
                    setOperations(
                        data.operations
                    )

                    notifyNewTrades(
                        data.operations
                    )
                }
            )
    }


    function notifyNewTrades(
        operations: OperationLogEntry[]
    ) {
        if (
            typeof Notification
            === "undefined"
        ) {
            return
        }

        if (
            Notification.permission
            !== "granted"
        ) {
            return
        }

        const storageKey = (
            "esmLastOperationSeenAt"
        )

        const stored = (
            window
            .localStorage
            .getItem(
                storageKey
            )
        )

        const lastSeen = (
            stored
            ? Date.parse(
                stored
            )
            : null
        )

        let maxTs: (
            number | null
        ) = lastSeen

        for (
            const operation
            of operations
        ) {
            const ts = (
                Date.parse(
                    operation
                    .created_at
                )
            )

            if (
                Number.isNaN(
                    ts
                )
            ) {
                continue
            }

            if (
                maxTs
                === null
                || ts
                > maxTs
            ) {
                maxTs = ts
            }

            if (
                lastSeen
                === null
            ) {
                //
                // Первый запуск:
                // фиксируем базовую
                // линию без спама.
                //
                continue
            }

            if (
                ts
                <= lastSeen
            ) {
                continue
            }

            if (
                operation
                .event_type
                !== "BUY"

                && (
                    operation
                    .event_type
                    !== "SELL"
                )
            ) {
                continue
            }

            try {
                new Notification(
                    "ESM: "
                    + (
                        operation
                        .event_type
                        === "BUY"
                            ? "Покупка"
                            : "Продажа"
                    )
                    + " "
                    + (
                        operation
                        .ticker
                        ?? ""
                    ),

                    {
                        body: (
                            operation
                            .details
                        ),
                    }
                )
            } catch {
                //
                // Уведомление не
                // имеет права ломать
                // интерфейс.
                //
            }
        }

        if (
            maxTs
            !== null
        ) {
            window
            .localStorage
            .setItem(
                storageKey,

                new Date(
                    maxTs
                )
                .toISOString()
            )
        }
    }


    function refreshDashboard() {
        getDashboard()
            .then(
                setDashboard
            )

            .catch(
                handleAuthError
            )
    }


    function handleAuthError(
        error: unknown
    ) {
        const message = (
            error
            instanceof Error
                ? error.message
                : ""
        )

        if (
            message
                .includes(
                    "Сессия истекла"
                )

            || message
                .includes(
                    "Требуется "
                    + "авториза"
                )
        ) {
            setAuthUser(
                null
            )

            setAuthMode(
                "login"
            )

            return
        }

        console.error(
            "API error:",
            error
        )
    }


    function refreshSessions() {
        getSessions()
            .then(
                data => {
                    setSessions(
                        data.sessions
                        ?? []
                    )
                }
            )
    }


    function refreshOverview() {
        getAccountsOverview()
            .then(
                setOverview
            )

            .catch(
                error => {
                    console.error(
                        "Overview error:",
                        error
                    )
                }
            )
    }


    function refreshLiveStatus() {
        getLiveStatus()
            .then(
                setLiveStatus
            )
            .catch(
                error => {
                    console.error(
                        "Live status error:",
                        error
                    )
                }
            )
    }


    function refreshTradingAccounts() {
        getTradingAccounts()
            .then(
                accounts => {
                    setTradingAccounts(
                        accounts
                    )

                    const liveAccounts =
                        accounts.filter(
                            account =>
                                account.enabled
                                && account.mode
                                === "live"
                                && account.broker === "tinvest"
                        )

                    setSelectedTradingAccountId(
                        current => {
                            if (
                                current
                                && liveAccounts
                                    .some(
                                        account =>
                                            account.id
                                            === current
                                    )
                            ) {
                                return current
                            }

                            if (
                                liveAccounts
                                    .length > 0
                            ) {
                                return (
                                    liveAccounts[0]
                                        .id
                                )
                            }

                            return null
                        }
                    )

                    const sandboxAccounts =
                        accounts.filter(
                            account =>
                                account.enabled
                                && account.mode
                                === "sandbox"
                        )

                    setSelectedSandboxAccountId(
                        current => {
                            if (
                                current
                                && sandboxAccounts
                                    .some(
                                        account =>
                                            account.id
                                            === current
                                    )
                            ) {
                                return current
                            }

                            return null
                        }
                    )
                }
            )
    }


    function resetValidation() {
        setLiveValidation(
            null
        )

        setStartError(
            null
        )
    }


    async function searchAvailableInstruments(
        value: string
    ) {
        const query =
            value.trim()

        if (!query) {
            setInstrumentSearchResults([])
            return
        }

        setIsSearchingInstruments(true)

        try {
            const data =
                await searchInstruments(
                    query,
                    tradingMode === "live"
                        ? selectedTradingAccountId
                        : selectedSandboxAccountId,
                    30
                )

            setInstrumentSearchResults(
                data.instruments
            )

        } catch (error) {
            console.error(
                "Instrument search error:",
                error
            )

            setInstrumentSearchResults([])

        } finally {
            setIsSearchingInstruments(false)
        }
    }


    function selectInstrumentSearchResult(
        item: InstrumentSearchResult
    ) {
        setNewTicker(
            item.ticker
        )

        setInstrumentSearchResults([])
    }


    function addInstrument() {
        const ticker =
            newTicker
                .trim()
                .toUpperCase()

        if (!ticker) {
            return
        }

        if (
            instruments.some(
                instrument =>
                    instrument.ticker
                        .toUpperCase()
                    === ticker
            )
        ) {
            setStartError(
                `Инструмент ${ticker} уже добавлен.`
            )
            return
        }

        setInstruments(
            current => [
                ...current,

                {
                    ticker,

                    levels:
                        newLevels,

                    quantity:
                        Math.max(
                            1,

                            Number(
                                newBaseQuantity
                                || "1"
                            )
                        ),

                    price: 0,

                    required_capital:
                        0,
                },
            ]
        )

        setNewTicker("")
        setNewLevels(20)
        setNewBaseQuantity("1")
        setInstrumentSearchResults([])

        setStartPlan(null)
        setStartResult(null)
        resetValidation()

        setModal(null)
    }


    function removeInstrument(
        ticker: string
    ) {
        setInstruments(
            current =>
                current.filter(
                    instrument =>
                        instrument.ticker
                        !== ticker
                )
        )

        setStartPlan(null)
        setStartResult(null)
        resetValidation()
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
                instrument.quantity
                ?? 1
            )
        )

        setModal(
            "edit-instrument"
        )
    }


    function saveInstrumentSettings() {
        if (!editingTicker) {
            return
        }

        setInstruments(
            current =>
                current.map(
                    instrument =>
                        instrument.ticker
                            === editingTicker

                            ? {
                                ...instrument,

                                levels:
                                    editLevels,

                                quantity:
                                    Math.max(
                                        1,

                                        Number(
                                            editQuantity
                                            || "1"
                                        )
                                    ),
                            }

                            : instrument
                )
        )

        setStartPlan(null)
        setStartResult(null)
        resetValidation()

        setModal(null)
    }


    function openNewSession() {
        setStartPlatform("")
        setInstruments([])
        setStartPlan(null)
        setStartResult(null)
        resetValidation()
        refreshTradingAccounts()
        setSelectionOpen(true)
    }

    function changeSessionPlatform(platform: string) {
        setStartPlatform(platform)
        setInstruments([])
        setStartPlan(null)
        setStartResult(null)
        resetValidation()
    }

    function changeSessionAccount(accountId: string | null) {
        setSelectedTradingAccountId(accountId)
        setInstruments([])
        setStartPlan(null)
        setStartResult(null)
        resetValidation()
    }

    function openStartModal() {
        setSelectionOpen(false)
        refreshTradingAccounts()

        setStartPlan(null)
        setStartResult(null)
        setLiveValidation(null)
        setStartError(null)

        setModal(
            "start-strategy"
        )
    }


    function buildStartInstruments() {
        return (
            instruments.map(
                instrument => ({
                    ticker:
                        instrument.ticker,

                    levels:
                        instrument.levels,

                    quantity:
                        instrument.quantity
                        ?? 1,
                })
            )
        )
    }


    async function validateLiveStrategy() {
        if (
            !selectedTradingAccountId
        ) {
            setStartError(
                "Выберите ESM LIVE счёт."
            )

            return
        }

        if (
            instruments.length
            === 0
        ) {
            setStartError(
                "Нет выбранных инструментов."
            )

            return
        }

        setIsValidating(true)
        setStartError(null)
        setLiveValidation(null)

        try {
            const result =
                await validateLiveStart(
                    selectedTradingAccountId,

                    buildStartInstruments()
                )

            setLiveValidation(
                result
            )

        } catch (error) {
            setStartError(
                error instanceof Error
                    ? error.message
                    : String(error)
            )

        } finally {
            setIsValidating(false)
        }
    }


    function calculatePlan() {
        setStartError(null)

        calculateStartPlan(
            buildStartInstruments(),

            tradingMode === "live"
                ? selectedTradingAccountId
                : selectedSandboxAccountId,

            tradingMode === "sandbox"
                ? 100000
                : null
        )
            .then(
                plan => {
                    setStartPlan(
                        plan
                    )

                    setStartResult(null)

                }
            )
            .catch(
                error => {
                    setStartError(
                        error instanceof Error
                            ? error.message
                            : String(error)
                    )
                }
            )
    }


    async function startStrategy() {
        if (
            tradingMode === "live"
        ) {
            if (
                !selectedTradingAccountId
            ) {
                setStartError(
                    "Выберите ESM LIVE счёт."
                )

                return
            }

            if (
                !liveValidation
                || !liveValidation.success
                || (
                    liveValidation
                        .trading_account_id
                    !== selectedTradingAccountId
                )
            ) {
                setStartError(
                    "Перед запуском выбранного ESM счёта "
                    + "выполните проверку LIVE-запуска."
                )

                return
            }
        } else if (!startPlan) {
            return
        }

        const force =
            tradingMode === "live"
                ? !liveValidation!.can_start
                : !startPlan!.can_start

        const startInstruments =
            buildStartInstruments()

        setIsStarting(true)
        setStartError(null)
        setStartResult(null)

        try {
            const result =
                tradingMode === "live"
                    ? await startLive(
                        force,
                        startInstruments,
                        selectedTradingAccountId
                    )
                    : await startSandbox(
                        force,
                        startInstruments,
                        selectedSandboxAccountId
                    )

            setStartResult(
                result
            )

            refreshAll()
            refreshLiveStatus()
            refreshTradingAccounts()

            if (
                result.status
                === "started"
            ) {
                window.setTimeout(
                    () => {
                        setModal(null)

                        setActiveTab(
                            "trading"
                        )
                    },
                    1200
                )
            }

        } catch (error) {
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
        getSession(
            ticker
        )
            .then(
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
        if (!window.confirm("Сессия остановится, все её текущие активы будут проданы по рынку. Подтвердить остановку?")) return
        stopSession(
            ticker
        )
            .then(
                result => {
                    if (
                        result.removed
                    ) {
                        setSelectedSession(null)
                        setModal(null)

                    } else {
                        setSelectedSession(current => current ? { ...current, status: result.status } : current)
                    }

                    refreshAll()
                }
            )
    }

    function drainSelectedSession(
        ticker: string
    ) {
        setStartError(null)

        drainSession(
            ticker
        )
            .then(
                result => {
                    setSelectedSession(
                        current => (
                            current
                                ? {
                                    ...current,
                                    status:
                                        result.status,
                                }
                                : current
                        )
                    )

                    refreshAll()
                }
            )
            .catch(
                error => {
                    setStartError(
                        error instanceof Error
                            ? error.message
                            : String(
                                error
                            )
                    )
                }
            )
    }

    function resumeSelectedSession(
        ticker: string
    ) {
        setStartError(null)

        resumeSession(
            ticker
        )
            .then(
                result => {
                    setSelectedSession(
                        current => (
                            current
                                ? {
                                    ...current,
                                    status:
                                        result.status,
                                }
                                : current
                        )
                    )

                    refreshAll()
                }
            )
            .catch(
                error => {
                    setStartError(
                        error instanceof Error
                            ? error.message
                            : String(
                                error
                            )
                    )
                }
            )
    }


    if (!authChecked) {
        return (
            <div
                style={{
                    padding: 20,

                    fontFamily:
                        "Arial, sans-serif",
                }}
            >
                Проверка доступа...
            </div>
        )
    }

    if (!authUser) {
        return (
            <AuthScreen
                initialMode={
                    authMode
                }

                onAuthenticated={
                    setAuthUser
                }
            />
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
                minHeight:
                    "100vh",

                background:
                    "var(--bg)",

                fontFamily:
                    "-apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif",
            }}
        >
            <div
                style={{
                    maxWidth: 560,

                    margin:
                        "0 auto",

                    padding:
                        "18px 16px 105px",
                }}
            >
                <Header
                    fullName={
                        authUser
                            .full_name
                    }
                />

                {activeTab === "home" && (
                    <>
                        <DashboardCard
                            dashboard={
                                dashboard
                            }
                        />

                        <AccountsSummary
                            accounts={
                                tradingAccounts
                            }

                            accountsDetail={
                                dashboard
                                    .accounts_detail
                                    ?? []
                            }

                        />

                        <OperationsHistoryCard
                            operations={
                                operations
                            }
                        />
                    </>
                )}

                {activeTab === "trading" && (
                    <>
                        <SectionTitle
                            title="Торговля"
                            compact
                            subtitle={
                                `${sessions.length} активных`
                            }

                            action={
                                <div
                                    style={{
                                        display:
                                        "flex",

                                        gap:
                                        6,
                                    }}
                                >
                                    <button
                                        onClick={() => setAccountsOpen(true)}
                                        style={smallPrimaryButton}
                                    >
                                        + Счёт
                                    </button>
                                    <button
                                        onClick={openNewSession}
                                        style={smallPrimaryButton}
                                    >
                                        + Сессия
                                    </button>
                                </div>
                            }
                        />

                        <SectionTitle title="Активные счета" />
                        <OverviewAccountsCard overview={overview} sessions={sessions} onOpenTicker={openSession} />
                        <TradingOverviewCard overview={overview} sessions={sessions} onOpenTicker={openSession} />
                    </>
                )}

                {selectionOpen && (
                    <AppModal
                        title="Новая сессия"
                        onClose={() => setSelectionOpen(false)}
                    >

                        <label style={{ display: "block", fontSize: 13 }}>
                            Платформа
                            <select aria-label="Платформа новой сессии" value={startPlatform} onChange={event => changeSessionPlatform(event.target.value)} style={{ width: "100%", marginTop: 6, padding: 10 }}>
                                <option value="">Выберите платформу</option>
                                <option value="tinvest">Т-Инвест</option>
                                <option value="bybit">Bybit</option>
                            </select>
                        </label>
                        {startPlatform === "bybit" && <BybitStartForm accounts={enabledLiveAccounts.filter(account => account.broker === "bybit")} onStarted={() => {
                            refreshAll()
                            refreshTradingAccounts()
                            setSelectionOpen(false)
                            setActiveTab("trading")
                        }} />}
                        {startPlatform === "tinvest" && <>
                            <label style={{ display: "block", marginTop: 12, fontSize: 13 }}>
                                Счёт Т-Инвест
                                <select aria-label="Счёт новой сессии Т-Инвест" value={selectedTradingAccountId ?? ""} onChange={event => changeSessionAccount(event.target.value || null)} style={{ width: "100%", marginTop: 6, padding: 10 }}>
                                    <option value="">Выберите счёт</option>
                                    {enabledLiveAccounts.filter(account => account.broker === "tinvest").map(account => <option key={account.id} value={account.id}>{account.name}</option>)}
                                </select>
                            </label>
                            {!enabledLiveAccounts.some(account => account.broker === "tinvest") && <div style={{ marginTop: 8, fontSize: 13 }}>Добавьте боевой счёт Т-Инвест.</div>}
                        {selectedTradingAccountId && <div
                            style={{
                                marginTop:
                                    12,
                            }}
                        >
                            <SectionTitle
                                title="Подбор инструментов"

                                subtitle={
                                    `${instruments.length} выбрано`
                                }

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

                            <InstrumentSelectionCard key={selectedTradingAccountId} tradingAccountId={selectedTradingAccountId} onSelect={selected => {
                                setInstruments(current => {
                                    const merged = new Map(current.map(item => [item.ticker, item]))
                                    selected.forEach(item => merged.set(item.ticker, item))
                                    return Array.from(merged.values())
                                })
                                setStartPlan(null)
                                setStartResult(null)
                                resetValidation()
                            }} />

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
                                    instruments.length
                                    === 0
                                }

                                style={
                                    primaryButton
                                }
                            >
                                Проверить и запустить
                            </button>
                        </div>}
                        </>}
                    </AppModal>
                )}

                {accountsOpen && (
                    <AppModal
                        title="Управление счетами"
                        onClose={() => {
                            setAccountsOpen(false)
                            refreshTradingAccounts()
                            refreshAll()
                        }}
                    >
                        <AccountsPanel />
                    </AppModal>
                )}

                {activeTab === "profile" && <UserSettingsCard user={authUser} onUpdated={setAuthUser} />}

                {activeTab === "settings" && (
                    <>
                        <div
                            style={{
                                display:
                                "flex",

                                justifyContent:
                                "space-between",

                                alignItems:
                                "center",

                                marginBottom:
                                14,
                            }}
                        >
                            <div
                                style={{
                                    fontSize:
                                    12,

                                    color:
                                    "var(--text-muted)",
                                }}
                            >
                                v{
                                    appVersion
                                    ?? "…"
                                }
                            </div>

                            <ThemeToggle />
                        </div>

                        <PlatformApiCard />

                        <NotificationSettingsCard />

                        <SecuritySettingsCard
                            deviceId={
                                deviceId
                            }

                            user={
                                authUser
                            }

                            onLoggedOut={() => {
                                setAuthUser(
                                    null
                                )

                                setAuthMode(
                                    "login"
                                )
                            }}
                        />
                    </>
                )}
            </div>

            <BottomNavigation
                activeTab={
                    activeTab
                }

                onChange={
                    setActiveTab
                }
            />

            {modal === "add-instrument" && (
                <AppModal
                    title=
                    "Добавить инструмент"

                    onClose={() => {
                        setInstrumentSearchResults([])
                        setModal(null)
                    }}
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

                        searchResults={
                            instrumentSearchResults
                        }

                        isSearching={
                            isSearchingInstruments
                        }

                        onTickerChange={
                            setNewTicker
                        }

                        onSearch={
                            searchAvailableInstruments
                        }

                        onSelect={
                            selectInstrumentSearchResult
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

                        onCancel={() => {
                            setInstrumentSearchResults([])
                            setModal(null)
                        }}
                    />
                </AppModal>
            )}

            {
                modal
                === "edit-instrument"

                && editingTicker

                && (
                    <AppModal
                        title=
                        "Настройка инструмента"

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
                )
            }

            {modal === "start-strategy" && (
                <AppModal
                    title=
                    "Запуск торговли"

                    onClose={() =>
                        setModal(null)
                    }
                >
                    <div style={{ fontSize: 13, marginBottom: 8 }}>Т-Инвест · {tradingAccounts.find(account => account.id === selectedTradingAccountId)?.name ?? "Счёт не выбран"}</div>
                    <button type="button" onClick={() => {setModal(null); setSelectionOpen(true)}} style={smallPrimaryButton}>Назад к инструментам</button>
                    {startPlatform === "tinvest" && <>
                    <div
                        style={
                            modeCardStyle
                        }
                    >
                        <span>
                            Режим
                        </span>

                        <b>
                            {
                                tradingMode
                                    === "live"
                                    ? "LIVE"
                                    : "SANDBOX"
                            }
                        </b>
                    </div>

                    {tradingMode === "live" && (
                        <div
                            style={
                                cardStyle
                            }
                        >
                            <div>
                                Торговый счёт
                            </div>

                            {enabledLiveAccounts.some(account => account.broker === "tinvest") ? (
                                <select
                                    value={
                                        selectedTradingAccountId
                                        ?? ""
                                    }

                                    onChange={
                                        event => {
                                             changeSessionAccount(event.target.value || null)
                                             setModal(null)
                                             setSelectionOpen(true)
                                        }
                                    }

                                    style={{
                                        width:
                                            "100%",

                                        marginTop:
                                            8,

                                        padding:
                                            10,
                                    }}
                                >
                                    {enabledLiveAccounts.filter(account => account.broker === "tinvest").map(
                                        account => (
                                            <option
                                                key={
                                                    account.id
                                                }

                                                value={
                                                    account.id
                                                }
                                            >
                                                {
                                                    account.name
                                                }
                                                {" · "}
                                                {
                                                    account
                                                        .broker_account_id
                                                }
                                            </option>
                                        )
                                    )}
                                </select>
                            ) : (
                                <div>
                                    ESM LIVE счета отсутствуют.
                                </div>
                            )}

                            {selectedTradingAccountId && (
                                <button
                                    onClick={
                                        validateLiveStrategy
                                    }

                                    disabled={
                                        isValidating
                                    }

                                    style={{
                                        ...primaryButton,

                                        marginTop:
                                            12,
                                    }}
                                >
                                    {
                                        isValidating
                                            ? "Проверка..."
                                            : "Проверить LIVE запуск"
                                    }
                                </button>
                            )}
                        </div>
                    )}

                    {tradingMode === "sandbox" && (
                        <div
                            style={
                                cardStyle
                            }
                        >
                            <div>
                                Торговый счёт
                            </div>

                            <select
                                value={
                                    selectedSandboxAccountId
                                    ?? ""
                                }

                                onChange={
                                    event => {
                                        setSelectedSandboxAccountId(
                                            event
                                                .target
                                                .value
                                            || null
                                        )

                                        setStartResult(
                                            null
                                        )
                                    }
                                }

                                style={{
                                    width:
                                        "100%",

                                    marginTop:
                                        8,

                                    padding:
                                        10,
                                }}
                            >
                                <option
                                    value=""
                                >
                                    Авто-выбор счёта
                                </option>

                                {enabledSandboxAccounts.map(
                                    account => (
                                        <option
                                            key={
                                                account.id
                                            }

                                            value={
                                                account.id
                                            }
                                        >
                                            {
                                                account.name
                                            }
                                            {" · "}
                                            {
                                                account
                                                    .broker_account_id
                                            }
                                        </option>
                                    )
                                )}
                            </select>

                            <div
                                style={{
                                    marginTop:
                                        8,

                                    fontSize:
                                        13,

                                    color:
                                        "var(--text-muted)",
                                }}
                            >
                                {
                                    selectedSandboxAccountId
                                        ? "Токен и sandbox-счёт берутся из выбранного счёта."
                                        : "Счёт и токен выбираются автоматически: первый активный T-Invest SANDBOX (токен из настроек счёта, .env не нужен)."
                                }
                            </div>
                        </div>
                    )}

                    {liveValidation && (
                        <LiveValidationCard
                            result={
                                liveValidation
                            }
                        />
                    )}

                    {startError && (
                        <div
                            style={
                                errorStyle
                            }
                        >
                            {
                                startError
                            }
                        </div>
                    )}

                    {tradingMode === "live" ? (
                        <>
                            {liveValidation && (
                                <div
                                    style={
                                        cardStyle
                                    }
                                >
                                    <button
                                        onClick={
                                            startStrategy
                                        }

                                        disabled={
                                            isStarting
                                            || !liveValidation.success
                                        }

                                        style={{
                                            ...primaryButton,
                                            opacity:
                                                isStarting
                                                || !liveValidation.success
                                                    ? 0.6
                                                    : 1,
                                        }}
                                    >
                                        {
                                            isStarting
                                                ? "Запуск..."
                                                : liveValidation.can_start
                                                    ? "Запустить LIVE"
                                                    : "Запустить принудительно"
                                        }
                                    </button>

                                    {!liveValidation.can_start && (
                                        <div
                                            style={{
                                                marginTop: 8,
                                                color: "var(--accent)",
                                                fontSize: 13,
                                            }}
                                        >
                                            Свободных средств меньше расчётной суммы.
                                            Запуск будет выполнен в принудительном режиме.
                                        </div>
                                    )}
                                </div>
                            )}
                        </>
                    ) : !startPlan ? (
                        <div
                            style={
                                cardStyle
                            }
                        >
                            <button
                                onClick={
                                    calculatePlan
                                }

                                style={
                                    primaryButton
                                }
                            >
                                Рассчитать капитал Sandbox
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

                            {isStarting && (
                                <div>
                                    Запуск...
                                </div>
                            )}
                        </>
                    )}
                    </>}
                </AppModal>
            )}

            {
                modal
                === "session-detail"

                && selectedSession

                && (
                    <AppModal
                        title={
                            selectedSession.ticker
                        }

                        onClose={() =>
                            setModal(null)
                        }
                    >
                        <SessionChartCard ticker={selectedSession.ticker} />
                        <SessionDetailCard
                            session={selectedSession}
                            onClose={() => setModal(null)}
                            onStop={stopSelectedSession}
                        />
                        <div
                            style={{
                                marginTop: 16,
                                marginBottom: 12,
                                padding: 12,
                                borderRadius: 12,
                                background:
                                    selectedSession.status
                                    === "DRAINING"
                                        ? "var(--accent-soft)"
                                        : "var(--card-soft)",
                            }}
                        >
                            <div
                                style={{
                                    fontWeight: 700,
                                    marginBottom: 6,
                                }}
                            >
                                Управление сессией
                            </div>

                            <div
                                style={{
                                    color: "var(--text-muted)",
                                    fontSize: 13,
                                    marginBottom: 10,
                                    lineHeight: 1.4,
                                }}
                            >
                                {
                                    selectedSession.status
                                    === "DRAINING"
                                        ? "Режим сушки активен. Сетка работает как обычно, пока есть хотя бы одна открытая позиция. При выходе в 0 сессия остановится автоматически."
                                        : "Сушка не меняет торговую логику текущей сетки. После полного выхода из позиций новая работа по активу не продолжится."
                                }
                            </div>

                            <button
                                onClick={() =>
                                    selectedSession.status
                                    === "DRAINING"
                                        ? resumeSelectedSession(
                                            selectedSession.ticker
                                        )
                                        : drainSelectedSession(
                                            selectedSession.ticker
                                        )
                                }

                                style={{
                                    width: "100%",
                                    padding: 12,
                                    borderRadius: 10,
                                    border: "none",
                                    background:
                                        selectedSession.status
                                        === "DRAINING"
                                            ? "var(--accent)"
                                            : "var(--accent)",
                                    color:
                                        "white",
                                    fontWeight: 700,
                                    cursor:
                                        "pointer",
                                }}
                            >
                                {
                                    selectedSession.status
                                    === "DRAINING"
                                        ? "Отменить сушку"
                                        : "Включить сушку"
                                }
                            </button>
                        </div>

                    </AppModal>
                )
            }
        </div>
    )
}


function formatDecimalValue(
    value: string | number,
    maximumFractionDigits = 2
): string {
    const numericValue = Number(
        value
    )

    if (
        Number.isNaN(
            numericValue
        )
    ) {
        return String(
            value
        )
    }

    return numericValue.toLocaleString(
        "ru-RU",
        {
            minimumFractionDigits: 0,
            maximumFractionDigits,
        }
    )
}


function formatMoneyValue(
    value: string | number
): string {
    return (
        `${formatDecimalValue(value, 2)} ₽`
    )
}


function formatPercentValue(
    value: string | number
): string {
    return (
        `${formatDecimalValue(value, 2)}%`
    )
}


function LiveValidationCard({
    result,
}: {
    result:
    LiveStartValidationResult
}) {
    return (
        <div
            style={{
                ...cardStyle,

                border:
                    result.can_start
                        ? "1px solid #86efac"
                        : "1px solid #fca5a5",
            }}
        >
            <h3
                style={{
                    marginTop:
                        0,
                }}
            >
                Проверка LIVE
            </h3>

            <ValidationRow
                label="Счёт"

                value={
                    result.account_name
                }
            />

            <ValidationRow
                label="Брокер"

                value={
                    result.broker
                }
            />

            <ValidationRow
                label="Свободные средства"

                value={
                    formatMoneyValue(
                        result.available_cash
                    )
                }
            />

            <ValidationRow
                label="Необходимо"

                value={
                    formatMoneyValue(
                        result.total_required_deposit
                    )
                }
            />

            <ValidationRow
                label="Остаток"

                value={
                    formatMoneyValue(
                        result.remaining_cash
                    )
                }
            />

            <ValidationRow
                label="Нехватка"

                value={
                    formatMoneyValue(
                        result.missing_cash
                    )
                }
            />

            <ValidationRow
                label="Комиссия BUY"

                value={
                    formatPercentValue(
                        result.buy_commission_percent
                    )
                }
            />

            <ValidationRow
                label="Комиссия SELL"

                value={
                    formatPercentValue(
                        result.sell_commission_percent
                    )
                }
            />

            <ValidationRow
                label="Запуск"

                value={
                    result.can_start
                        ? "Разрешён"
                        : "Недостаточно средств"
                }
            />

            <div
                style={{
                    marginTop:
                        16,
                }}
            >
                {result.instruments.map(
                    instrument => (
                        <div
                            key={
                                instrument
                                    .instrument_uid
                            }

                            style={{
                                padding:
                                    "12px 0",

                                borderTop:
                                    "1px solid var(--border)",
                            }}
                        >
                            <div
                                style={{
                                    fontSize: 17,
                                    fontWeight: 700,
                                    marginBottom: 8,
                                }}
                            >
                                {
                                    instrument.ticker
                                }
                            </div>

                            <ValidationRow
                                label="Текущая цена"
                                value={
                                    formatMoneyValue(
                                        instrument.current_price
                                    )
                                }
                            />

                            <ValidationRow
                                label="Нижняя граница сетки"
                                value={
                                    formatMoneyValue(
                                        instrument.min_grid_price
                                    )
                                }
                            />

                            <ValidationRow
                                label="Шаг сетки"
                                value={
                                    formatMoneyValue(
                                        instrument.grid_step
                                    )
                                }
                            />

                            <ValidationRow
                                label="Уровней"
                                value={
                                    String(
                                        instrument.levels_count
                                    )
                                }
                            />

                            <ValidationRow
                                label="Количество"
                                value={
                                    String(
                                        instrument.quantity
                                    )
                                }
                            />
                        </div>
                    )
                )}
            </div>
        </div>
    )
}


function ValidationRow({
    label,
    value,
}: {
    label: string
    value: string
}) {
    return (
        <div
            style={{
                display:
                    "flex",

                justifyContent:
                    "space-between",

                alignItems:
                    "flex-start",

                gap:
                    12,

                padding:
                    "6px 0",
            }}
        >
            <span
                style={{
                    color:
                        "var(--text-muted)",
                }}
            >
                {
                    label
                }
            </span>

            <b
                style={{
                    textAlign:
                        "right",
                }}
            >
                {
                    value
                }
            </b>
        </div>
    )
}


function Header({
    fullName,
}: {
    fullName: string | null
}) {
    return (
        <div
            style={{
                marginBottom:
                    20,
            }}
        >
            <h1>
                {
                    fullName
                    || "Портфель"
                }
            </h1>
        </div>
    )
}


function SectionTitle({
    title,
    subtitle,
    action,
    compact = false,
}: {
    title: string
    subtitle?: string
    action?: React.ReactNode
    compact?: boolean
}) {
    return (
        <div
            style={{
                display:
                    "flex",

                justifyContent:
                    "space-between",

                marginBottom:
                    compact ? 6 : 16,
                alignItems: "center",
                gap: 8,
            }}
        >
            <div style={{ display: compact ? "flex" : "block", alignItems: "baseline", gap: 8 }}>
                <h2 style={compact ? { margin: 0, fontSize: 18 } : undefined}>
                    {
                        title
                    }
                </h2>

                {
                    subtitle
                    && (
                        <div>
                            {
                                subtitle
                            }
                        </div>
                    )
                }
            </div>

            {
                action
            }
        </div>
    )
}


function AccountsSummary({
    accounts,
    accountsDetail,
}: {
    accounts:
    TradingAccount[]

    accountsDetail:
    DashboardAccountDetail[]

}) {
    const detailById = (
        new Map(
            accountsDetail.map(
                detail => [
                    detail.id,

                    detail,
                ]
            )
        )
    )

    return (
        <div
            style={{
                background: "var(--card)",

                borderRadius:
                14,

                padding:
                13,

                marginTop:
                10,
            }}
        >
            <div
                style={{
                    display:
                    "flex",

                    justifyContent:
                    "space-between",

                    alignItems:
                    "center",

                    marginBottom:
                    10,
                }}
            >
                <h3
                    style={{
                        margin:
                        0,
                    }}
                >
                    Счета
                </h3>

                <span style={{ color: "var(--text-muted)", fontSize: 12 }}>
                    {accounts.length}
                </span>
            </div>

            {accounts.length === 0 ? (
                <div
                    style={{
                        color:
                        "var(--text-muted)",

                        fontSize:
                        13,
                    }}
                >
                    Счета не добавлены.
                </div>
            ) : (
                accounts.map(
                    account => {
                        const detail = (
                            detailById.get(
                                account.id
                            )
                        )

                        const balance = (
                            detail
                                ?.balance
                                ?? null
                        )

                        const pnlToday = (
                            detail
                                ?.pnl_today
                                ?? null
                        )

                        return (
                            <div
                                key={
                                    account.id
                                }

                                style={{
                                    display:
                                    "flex",

                                    alignItems:
                                    "center",

                                    gap:
                                    12,

                                    padding:
                                    "10px 0",

                                    borderTop:
                                    "1px solid var(--border)",
                                }}
                            >
                                <div
                                    style={{
                                        width:
                                        38,

                                        height:
                                        38,

                                        borderRadius:
                                        12,

                                        flexShrink:
                                        0,

                                        display:
                                        "flex",

                                        alignItems:
                                        "center",

                                        justifyContent:
                                        "center",

                                        background:
                                        "var(--card-soft)",

                                        color:
                                        "var(--accent)",

                                        fontSize:
                                        17,

                                        fontWeight:
                                        700,
                                    }}
                                >
                                    {
                                        account
                                            .name
                                            .trim()
                                            .charAt(
                                                0
                                            )
                                            .toUpperCase()
                                        || "•"
                                    }
                                </div>

                                <div
                                    style={{
                                        minWidth:
                                        0,

                                        flex:
                                        1,
                                    }}
                                >
                                    <div
                                        style={{
                                            fontWeight:
                                            600,

                                            fontSize:
                                            14,

                                            whiteSpace:
                                            "nowrap",

                                            overflow:
                                            "hidden",

                                            textOverflow:
                                            "ellipsis",
                                        }}
                                    >
                                        {
                                            account.name
                                        }
                                    </div>

                                    <div
                                        style={{
                                            color:
                                            "var(--text-muted)",

                                            fontSize:
                                            12,
                                        }}
                                    >
                                        {
                                            account.broker
                                        }
                                        {" · "}
                                        {
                                            detail
                                                ?.currency
                                                ?? "RUB"
                                        }
                                    </div>
                                </div>

                                <div
                                    style={{
                                        display:
                                        "flex",

                                        flexDirection:
                                        "column",

                                        alignItems:
                                        "flex-end",

                                        gap:
                                        2,
                                    }}
                                >
                                    <div
                                        style={{
                                            fontWeight:
                                            700,

                                            fontSize:
                                            15,
                                        }}
                                    >
                                        {
                                            balance
                                            === null
                                                ? "—"
                                                : `${
                                                    balance.toLocaleString(
                                                        "ru-RU",
                                                        {
                                                            maximumFractionDigits: 2,
                                                        }
                                                    )
                                                } ${
                                                    currencySign(
                                                        detail
                                                            ?.currency
                                                            ?? "RUB"
                                                    )
                                                }`
                                        }
                                    </div>

                                    <div
                                        style={{
                                            fontSize:
                                            12,

                                            fontWeight:
                                            600,

                                            color:
                                            pnlToday
                                            === null
                                                ? "var(--text-dim)"
                                                : (
                                                    pnlToday
                                                    >= 0
                                                        ? "var(--profit)"
                                                        : "var(--loss)"
                                                ),
                                        }}
                                    >
                                        {
                                            pnlToday
                                            === null
                                                ? "—"
                                                : `${
                                                    pnlToday
                                                    > 0
                                                        ? "+"
                                                        : ""
                                                }${
                                                    pnlToday.toLocaleString(
                                                        "ru-RU",
                                                        {
                                                            maximumFractionDigits: 2,
                                                        }
                                                    )
                                                } ${
                                                    currencySign(
                                                        detail
                                                            ?.currency
                                                            ?? "RUB"
                                                    )
                                                }`
                                        }
                                    </div>

                                    <div
                                        style={{
                                            fontSize:
                                            11,

                                            fontWeight:
                                            700,

                                            padding:
                                            "2px 8px",

                                            borderRadius:
                                            8,

                                            background: (
                                                detail
                                                    ?.mode
                                                    ?? account.mode
                                            )
                                            === "live"
                                                ? "var(--accent-soft)"
                                                : "var(--card-soft)",

                                            color: (
                                                detail
                                                    ?.mode
                                                    ?? account.mode
                                            )
                                            === "live"
                                                ? "var(--accent)"
                                                : "var(--text-muted)",

                                            whiteSpace:
                                            "nowrap",
                                        }}
                                    >
                                        {
                                            (
                                                detail
                                                    ?.mode
                                                    ?? account.mode
                                            )
                                            === "live"
                                                ? "LIVE"
                                                : "SANDBOX"
                                        }

                                        {
                                            !(
                                                detail
                                                    ?.enabled
                                                    ?? account.enabled
                                            )
                                            && (
                                                " · выкл"
                                            )
                                        }
                                    </div>
                                </div>
                            </div>
                        )
                    }
                )
            )}
        </div>
    )
}


function currencySign(
    currency: string
): string {
    if (
        currency
        === "RUB"
    ) {
        return "₽"
    }

    return currency
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
            style={
                cardStyle
            }
        >
            <h3>
                {
                    title
                }
            </h3>

            <p>
                {
                    text
                }
            </p>

            <button
                onClick={
                    onClick
                }

                style={
                    primaryButton
                }
            >
                {
                    button
                }
            </button>
        </div>
    )
}


const primaryButton = {
    width:
        "100%",

    padding:
        14,

    borderRadius:
        13,

    border:
        "none",

    background:
        "var(--accent)",

    color:
        "white",

    fontSize:
        16,

    fontWeight:
        600,

    cursor:
        "pointer",
}


const smallPrimaryButton = {
    padding:
        "6px 10px",

    borderRadius:
        11,

    border:
        "none",

    background:
        "var(--accent)",

    color:
        "white",

    fontWeight:
        600,

    cursor:
        "pointer",
}


const cardStyle = {
    background: "var(--card)",

    borderRadius:
        14,

    padding:
        13,

    marginTop:
        10,
}


const modeCardStyle = {
    ...cardStyle,

    display:
        "flex",

    justifyContent:
        "space-between",

    gap:
        12,
}


const errorStyle = {
    marginTop:
        10,

    padding:
        12,

    borderRadius:
        12,

    background:
        "var(--loss-soft)",

    color:
        "var(--loss)",

    fontSize:
        14,

    wordBreak:
        "break-word" as const,
}
