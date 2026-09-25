import {
    useEffect,
    useState,
} from "react"

import {
    calculateStartPlan,
    drainSession,
    getApiUsage,
    getDashboard,
    getInstruments,
    getLiveStatus,
    getRunnerStatus,
    getSession,
    getSessions,
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
    AddInstrumentForm,
} from "./components/AddInstrumentForm"

import {
    ApiUsageCard,
} from "./components/ApiUsageCard"

import {
    AppModal,
} from "./components/AppModal"

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
    LiveStatusCard,
} from "./components/LiveStatusCard"

import {
    RunnerStatusCard,
} from "./components/RunnerStatusCard"

import {
    SessionDetailCard,
} from "./components/SessionDetailCard"

import {
    SessionsCard,
} from "./components/SessionsCard"

import {
    StartPlanCard,
} from "./components/StartPlanCard"

import type {
    TradingAccount,
} from "./accounts/types"

import type {
    ActiveSession,
    ApiUsage,
    Dashboard,
    Instrument,
    InstrumentSearchResult,
    LiveStartValidationResult,
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
        apiUsage,
        setApiUsage,
    ] = useState<
        ApiUsage | null
    >(null)

    const [
        runners,
        setRunners,
    ] = useState<
        RunnerStatus[]
    >([])

    const [
        liveStatus,
        setLiveStatus,
    ] = useState<
        LiveStatus | null
    >(null)

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


    const tradingMode =
        liveStatus
            ?.trading_mode
            === "live"
            ? "live"
            : "sandbox"


    const liveTradingEnabled =
        liveStatus
            ?.live_trading_enabled
        === true


    const enabledLiveAccounts =
        tradingAccounts
            .filter(
                account =>
                    account.enabled
                    && account.mode
                    === "live"
            )


    useEffect(
        () => {
            refreshAll()

            refreshLiveStatus()

            refreshTradingAccounts()

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
                    5000
                )

            return () =>
                window
                    .clearInterval(
                        intervalId
                    )
        },
        []
    )


    function refreshAll() {
        refreshDashboard()
        refreshSessions()
        refreshApiUsage()
        refreshRunnerStatus()
    }


    function refreshDashboard() {
        getDashboard()
            .then(
                setDashboard
            )
    }


    function refreshSessions() {
        getSessions()
            .then(
                data => {
                    setSessions(
                        data.sessions
                    )
                }
            )
    }


    function refreshApiUsage() {
        getApiUsage()
            .then(
                setApiUsage
            )
    }


    function refreshRunnerStatus() {
        getRunnerStatus()
            .then(
                data => {
                    setRunners(
                        data.runners
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
                    selectedTradingAccountId,
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


    function openStartModal() {
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
                : null,

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

                    refreshApiUsage()
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
                !liveTradingEnabled
            ) {
                setStartError(
                    "Live trading отключен. "
                    + "LIVE_TRADING_ENABLED=0"
                )

                return
            }

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
                        null
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
                            "sessions"
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
                        setSelectedSession(
                            result
                        )
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
                            : String(error)
                    )
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
                minHeight:
                    "100vh",

                background:
                    "#f4f6f8",

                fontFamily:
                    "-apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif",
            }}
        >
            <div
                style={{
                    maxWidth:
                        activeTab
                            === "accounts"
                            ? 900
                            : 560,

                    margin:
                        "0 auto",

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

                {activeTab === "sessions" && (
                    <>
                        <SectionTitle
                            title="Сессии"

                            subtitle={
                                `${sessions.length} активных`
                            }
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
                                title=
                                "Нет активных сессий"

                                text=
                                "Запусти первую стратегию"

                                button=
                                "Запустить"

                                onClick={
                                    openStartModal
                                }
                            />
                        )}
                    </>
                )}

                {activeTab === "instruments" && (
                    <>
                        <SectionTitle
                            title="Инструменты"

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
                            Запустить
                        </button>
                    </>
                )}

                {activeTab === "accounts" && (
                    <>
                        <SectionTitle
                            title="Счета"

                            subtitle=
                            "Управление торговыми аккаунтами"
                        />

                        <AccountsPanel />
                    </>
                )}

                {activeTab === "api" && (
                    <>
                        <SectionTitle
                            title=
                            "API и Runner"

                            subtitle=
                            "Монитор нагрузки"
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

                {activeTab === "settings" && (
                    <>
                        <SectionTitle
                            title="Настройки"

                            subtitle=
                            "ESM Trade System v1.1.0-dev"
                        />

                        <LiveStatusCard
                            status={
                                liveStatus
                            }
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

                            {enabledLiveAccounts.length > 0 ? (
                                <select
                                    value={
                                        selectedTradingAccountId
                                        ?? ""
                                    }

                                    onChange={
                                        event => {
                                            setSelectedTradingAccountId(
                                                event
                                                    .target
                                                    .value
                                                || null
                                            )

                                            setLiveValidation(
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
                                    {enabledLiveAccounts.map(
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
                                                color: "#9a3412",
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
                        <div
                            style={{
                                marginBottom: 12,
                                padding: 12,
                                borderRadius: 12,
                                background:
                                    selectedSession.status
                                    === "DRAINING"
                                        ? "#fff7ed"
                                        : "#f9fafb",
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
                                    color: "#6b7280",
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
                                    drainSelectedSession(
                                        selectedSession.ticker
                                    )
                                }
                                disabled={
                                    selectedSession.status
                                    === "DRAINING"
                                }
                                style={{
                                    width: "100%",
                                    padding: 12,
                                    borderRadius: 10,
                                    border: "none",
                                    background:
                                        selectedSession.status
                                        === "DRAINING"
                                            ? "#d1d5db"
                                            : "#f59e0b",
                                    color:
                                        selectedSession.status
                                        === "DRAINING"
                                            ? "#4b5563"
                                            : "white",
                                    fontWeight: 700,
                                    cursor:
                                        selectedSession.status
                                        === "DRAINING"
                                            ? "default"
                                            : "pointer",
                                }}
                            >
                                {
                                    selectedSession.status
                                    === "DRAINING"
                                        ? "Сушка активна"
                                        : "Включить сушку"
                                }
                            </button>
                        </div>

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
                                    "1px solid #e5e7eb",
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
                        "#6b7280",
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


function Header() {
    return (
        <div
            style={{
                marginBottom:
                    20,
            }}
        >
            <div>
                ESM Trade System
            </div>

            <h1>
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
                display:
                    "flex",

                justifyContent:
                    "space-between",

                marginBottom:
                    16,
            }}
        >
            <div>
                <h2>
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


function QuickActions({
    sessionsCount,
    tradingMode,
    onStart,
    onSessions,
}: {
    sessionsCount: number

    tradingMode:
    "sandbox"
    | "live"

    onStart:
    () => void

    onSessions:
    () => void
}) {
    return (
        <div
            style={{
                display:
                    "grid",

                gridTemplateColumns:
                    "1fr 1fr",

                gap:
                    10,

                marginBottom:
                    16,
            }}
        >
            <button
                onClick={
                    onStart
                }

                style={
                    primaryButton
                }
            >
                {
                    tradingMode
                        === "live"
                        ? "+ Торговать"
                        : "+ Запустить"
                }
            </button>

            <button
                onClick={
                    onSessions
                }

                style={
                    primaryButton
                }
            >
                Сессии (
                {
                    sessionsCount
                }
                )
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
        "#2563eb",

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
        "10px 13px",

    borderRadius:
        11,

    border:
        "none",

    background:
        "#2563eb",

    color:
        "white",

    fontWeight:
        600,

    cursor:
        "pointer",
}


const cardStyle = {
    background:
        "white",

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
        "#fee2e2",

    color:
        "#991b1b",

    fontSize:
        14,

    wordBreak:
        "break-word" as const,
}
