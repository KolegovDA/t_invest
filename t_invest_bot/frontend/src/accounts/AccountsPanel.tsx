import {
    useEffect,
    useMemo,
    useState,
} from "react"

import {
    AccountMovementsCard,
} from "./AccountMovementsCard"

import {
    createTradingAccount,
    deleteTradingAccount,
    discoverPlatformAccounts,
    getBrokers,
    getPlatforms,
    getTradingAccountPortfolio,
    getTradingAccounts,
    testTradingAccount,
    updateTradingAccount,
} from "./api"

import type {
    BrokerConnectionResult,
    BrokerInfo,
    BrokerPortfolio,
    CommissionMode,
    CreateTradingAccountPayload,
    DiscoveredBrokerAccount,
    PlatformConnection,
    TradingAccount,
    TradingAccountMode,
} from "./types"


const platformLabels: Record<
    string,
    string
> = {
    tinvest:
    "Т-Инвест",

    bybit:
    "Bybit",
}


const modeLabels: Record<
    string,
    string
> = {
    live:
    "Боевой",

    sandbox:
    "Песочница",
}


type FormState = {
    name: string

    platformId:
        string | null

    broker: string

    brokerAccountId: string

    mode: TradingAccountMode

    baseCurrency: string

    commissionMode: CommissionMode

    customBuyCommission: string

    customSellCommission: string

    credentials: Record<string, string>

    enabled: boolean
}


const emptyForm: FormState = {
    name: "",

    platformId: null,

    broker: "tinvest",

    brokerAccountId: "",

    mode: "live",

    baseCurrency: "USDT",

    commissionMode: "auto",

    customBuyCommission: "0.30",

    customSellCommission: "0.30",

    credentials: {},

    enabled: true,
}


function formatMoney(
    value: string | null
): string {
    if (value === null) {
        return "—"
    }

    const numeric =
        Number(value)

    if (
        Number.isNaN(
            numeric
        )
    ) {
        return value
    }

    return (
        numeric.toLocaleString(
            "ru-RU",
            {
                maximumFractionDigits: 2,
            }
        )
        + " ₽"
    )
}


function commissionLabel(
    mode: CommissionMode
): string {
    switch (mode) {
        case "auto":
            return "Автоматически"

        case "investor_030":
            return "Инвестор — 0,30%"

        case "trader_005":
            return "Трейдер — 0,05%"

        case "custom":
            return "Пользовательская"

        default:
            return mode
    }
}


export function AccountsPanel() {
    const [
        brokers,
        setBrokers,
    ] = useState<
        BrokerInfo[]
    >([])

    const [
        platforms,
        setPlatforms,
    ] = useState<
        PlatformConnection[]
    >([])

    const [
        accounts,
        setAccounts,
    ] = useState<
        TradingAccount[]
    >([])

    const [
        portfolios,
        setPortfolios,
    ] = useState<
        Record<
            string,
            BrokerPortfolio
        >
    >({})

    const [
        form,
        setForm,
    ] = useState<FormState>(
        emptyForm
    )

    const [
        editingId,
        setEditingId,
    ] = useState<
        string | null
    >(null)

    const [
        connectionResult,
        setConnectionResult,
    ] = useState<
        Record<
            string,
            BrokerConnectionResult
        >
    >({})

    const [
        loading,
        setLoading,
    ] = useState(
        false
    )

    const [
        error,
        setError,
    ] = useState<
        string | null
    >(null)

    const [
        discovered,
        setDiscovered,
    ] = useState<
        DiscoveredBrokerAccount[]
    >([])

    const [
        discovering,
        setDiscovering,
    ] = useState(
        false
    )

    const [
        discoveryError,
        setDiscoveryError,
    ] = useState<
        string | null
    >(null)


    const selectedBroker =
        useMemo(
            () =>
                brokers.find(
                    broker =>
                        broker.id
                        === form.broker
                ),
            [
                brokers,
                form.broker,
            ]
        )


    const selectedPlatform =
        useMemo(
            () =>
                platforms.find(
                    platform =>
                        platform.id
                        === form.platformId
                ),
            [
                platforms,
                form.platformId,
            ]
        )


    async function reload() {
        const [
            loadedBrokers,
            loadedAccounts,
            loadedPlatforms,
        ] = await Promise.all([
            getBrokers(),
            getTradingAccounts(),
            getPlatforms(),
        ])

        setBrokers(
            loadedBrokers
        )

        setAccounts(
            loadedAccounts
        )

        setPlatforms(
            loadedPlatforms
        )
    }


    useEffect(
        () => {
            reload()
                .catch(
                    currentError => {
                        setError(
                            currentError
                                instanceof Error
                                ? currentError.message
                                : String(
                                    currentError
                                )
                        )
                    }
                )
        },
        []
    )


    function resetForm() {
        setForm({
            ...emptyForm,
            credentials: {},
        })

        setEditingId(
            null
        )

        setError(
            null
        )

        setDiscovered(
            []
        )

        setDiscoveryError(
            null
        )
    }


    function updateCredential(
        key: string,
        value: string
    ) {
        setForm(
            previous => ({
                ...previous,

                credentials: {
                    ...previous
                        .credentials,

                    [key]:
                        value,
                },
            })
        )
    }


    function clearDiscovered() {
        setDiscovered(
            []
        )

        setDiscoveryError(
            null
        )
    }


    function selectPlatform(
        platform: PlatformConnection
    ) {
        setForm(
            previous => ({
                ...previous,

                platformId:
                    platform.id,

                broker:
                    platform.broker,

                mode:
                    platform.mode,
                brokerAccountId: platform.broker === "bybit" ? "UNIFIED" : "",
                commissionMode: "auto",
            })
        )

        clearDiscovered()
    }


    async function loadPlatformAccounts() {
        if (
            form.platformId
            === null
        ) {
            return
        }

        setDiscovering(
            true
        )

        setDiscoveryError(
            null
        )

        try {
            const result =
                await discoverPlatformAccounts(
                    form
                        .platformId
                )

            if (
                !result
                    .success
            ) {
                setDiscovered(
                    []
                )

                setDiscoveryError(
                    result
                        .error
                    ?? "Не удалось получить счета платформы"
                )

                return
            }

            setDiscovered(
                result
                    .accounts
            )

            if (
                result
                    .accounts
                    .length
                === 0
            ) {
                setDiscoveryError(
                    "У платформы счета не найдены"
                )
            }

        } catch (
        currentError
        ) {
            setDiscovered(
                []
            )

            setDiscoveryError(
                currentError instanceof Error
                    ? currentError.message
                    : String(
                        currentError
                    )
            )

        } finally {
            setDiscovering(
                false
            )
        }
    }


    function selectDiscoveredAccount(
        account: DiscoveredBrokerAccount
    ) {
        setForm(
            previous => ({
                ...previous,

                brokerAccountId:
                    account
                        .broker_account_id,

                name:
                    previous
                        .name
                        .trim()
                    === ""
                        ? account.name
                        : previous
                            .name,
            })
        )
    }


    async function saveAccount() {
        setLoading(
            true
        )

        setError(
            null
        )

        try {
            const credentials =
                Object.fromEntries(
                    Object.entries(
                        form.credentials
                    )
                        .filter(
                            ([, value]) =>
                                value
                                    .trim()
                                !== ""
                        )
                )

            if (
                editingId
                === null
                && selectedPlatform
                    === undefined
            ) {
                throw new Error(
                    "Выберите подключённую платформу (вкладка «Настройки»)"
                )
            }

            if (
                editingId
                === null
            ) {
                const payload:
                    CreateTradingAccountPayload = {
                    name:
                        form.name,

                    broker:
                        selectedPlatform.broker as CreateTradingAccountPayload["broker"],

                    broker_account_id:
                        form
                            .brokerAccountId,

                    platform_id:
                        selectedPlatform.id,

                    mode:
                        form.mode,

                    ...(form.broker === "bybit"
                        ? {
                            base_currency:
                                form
                                    .baseCurrency,
                        }
                        : {}),

                    commission_mode:
                        form
                            .commissionMode,

                    enabled:
                        form.enabled,
                }

                if (
                    form
                        .commissionMode
                    === "custom"
                ) {
                    payload
                        .custom_buy_commission_percent =
                        form
                            .customBuyCommission

                    payload
                        .custom_sell_commission_percent =
                        form
                            .customSellCommission
                }

                await createTradingAccount(
                    payload
                )

            } else {
                const payload: {
                    name: string
                    broker_account_id: string
                    mode: TradingAccountMode
                    commission_mode: CommissionMode
                    enabled: boolean
                    credentials?: Record<string, string>
                    custom_buy_commission_percent?: string
                    custom_sell_commission_percent?: string
                } = {
                    name:
                        form.name,

                    broker_account_id:
                        form
                            .brokerAccountId,

                    mode:
                        form.mode,

                    ...(form.broker === "bybit"
                        ? {
                            base_currency:
                                form
                                    .baseCurrency,
                        }
                        : {}),

                    commission_mode:
                        form
                            .commissionMode,

                    enabled:
                        form.enabled,
                }

                if (
                    Object.keys(
                        credentials
                    ).length
                    > 0
                ) {
                    payload.credentials =
                        credentials
                }

                if (
                    form
                        .commissionMode
                    === "custom"
                ) {
                    payload
                        .custom_buy_commission_percent =
                        form
                            .customBuyCommission

                    payload
                        .custom_sell_commission_percent =
                        form
                            .customSellCommission
                }

                await updateTradingAccount(
                    editingId,
                    payload
                )
            }

            await reload()

            resetForm()

        } catch (
        currentError
        ) {
            setError(
                currentError
                    instanceof Error
                    ? currentError.message
                    : String(
                        currentError
                    )
            )

        } finally {
            setLoading(
                false
            )
        }
    }


    function editAccount(
        account: TradingAccount
    ) {
        setEditingId(
            account.id
        )

        setForm({
            name:
                account.name,

            platformId: null,

            broker:
                account.broker,

            brokerAccountId:
                account
                    .broker_account_id,

            mode:
                account.mode,

            baseCurrency:
                account
                    .base_currency
                ?? "USDT",

            commissionMode:
                account
                    .commission_mode,

            customBuyCommission:
                account
                    .custom_buy_commission_percent
                ?? "0.30",

            customSellCommission:
                account
                    .custom_sell_commission_percent
                ?? "0.30",

            credentials: {},

            enabled:
                account.enabled,
        })

        setError(
            null
        )

        window.scrollTo({
            top: 0,
            behavior: "smooth",
        })
    }


    async function removeAccount(
        account: TradingAccount
    ) {
        const accepted =
            window.confirm(
                `Удалить счёт "${account.name}"?`
            )

        if (
            !accepted
        ) {
            return
        }

        try {
            setError(
                null
            )

            await deleteTradingAccount(
                account.id
            )

            setPortfolios(
                previous => {
                    const next = {
                        ...previous,
                    }

                    delete next[
                        account.id
                    ]

                    return next
                }
            )

            setConnectionResult(
                previous => {
                    const next = {
                        ...previous,
                    }

                    delete next[
                        account.id
                    ]

                    return next
                }
            )

            if (
                editingId
                === account.id
            ) {
                resetForm()
            }

            await reload()

        } catch (
        currentError
        ) {
            setError(
                currentError
                    instanceof Error
                    ? currentError.message
                    : String(
                        currentError
                    )
            )
        }
    }


    async function testConnection(
        account: TradingAccount
    ) {
        try {
            setError(
                null
            )

            const result =
                await testTradingAccount(
                    account.id
                )

            setConnectionResult(
                previous => ({
                    ...previous,

                    [account.id]:
                        result,
                })
            )

            if (
                result.success
                && result
                    .account_found
            ) {
                const portfolio =
                    await getTradingAccountPortfolio(
                        account.id
                    )

                setPortfolios(
                    previous => ({
                        ...previous,

                        [account.id]:
                            portfolio,
                    })
                )
            }

        } catch (
        currentError
        ) {
            setError(
                currentError
                    instanceof Error
                    ? currentError.message
                    : String(
                        currentError
                    )
            )
        }
    }


    return (
        <div
            style={{
                display:
                    "grid",

                gap:
                    20,
            }}
        >
            <section
                style={{
                    background: "var(--card)",

                    borderRadius:
                        18,

                    padding:
                        20,

                    boxShadow:
                        "0 8px 28px rgba(0,0,0,0.06)",
                }}
            >
                <div
                    style={{
                        display:
                            "flex",

                        justifyContent:
                            "space-between",

                        gap:
                            16,

                        alignItems:
                            "center",

                        marginBottom:
                            18,
                    }}
                >
                    <div>
                        <h2
                            style={{
                                margin:
                                    0,
                            }}
                        >
                            {
                                editingId
                                    ? "Редактирование счёта"
                                    : "Добавить торговый счёт"
                            }
                        </h2>
                    </div>

                    {
                        editingId
                        && (
                            <button
                                type="button"

                                onClick={
                                    resetForm
                                }
                            >
                                Отмена
                            </button>
                        )
                    }
                </div>

                <div
                    style={{
                        display:
                            "grid",

                        gridTemplateColumns:
                            "repeat(auto-fit, minmax(220px, 1fr))",

                        gap:
                            14,
                    }}
                >
                    <label>
                        Название счёта

                        <input
                            value={
                                form.name
                            }

                            onChange={
                                event =>
                                    setForm(
                                        previous => ({
                                            ...previous,

                                            name:
                                                event
                                                    .target
                                                    .value,
                                        })
                                    )
                            }

                            placeholder=
                            "Основной счёт"

                            style={{
                                width:
                                    "100%",

                                marginTop:
                                    6,
                            }}
                        />
                    </label>

                    {
                        editingId
                        !== null
                        ? (
                            <label>
                                Брокер

                                <select
                                    value={
                                        form.broker
                                    }

                                    disabled

                                    style={{
                                        width:
                                            "100%",

                                        marginTop:
                                            6,
                                    }}
                                >
                                    <option
                                        value={
                                            form.broker
                                        }
                                    >
                                        {
                                            platformLabels[
                                                form.broker
                                            ]
                                            ?? form.broker
                                        }
                                    </option>
                                </select>
                            </label>
                        )
                        : (
                            <label>
                                Платформа

                                <select
                                    value={
                                        form.platformId
                                        ?? ""
                                    }

                                    onChange={
                                        event => {
                                            const platform = (
                                                platforms.find(
                                                    item =>
                                                        item.id
                                                        === event
                                                            .target
                                                            .value
                                                )
                                            )

                                            if (
                                                platform
                                            ) {
                                                selectPlatform(
                                                    platform
                                                )
                                            }
                                        }
                                    }

                                    style={{
                                        width:
                                            "100%",

                                        marginTop:
                                            6,
                                    }}
                                >
                                    <option
                                        value=""
                                        disabled
                                    >
                                        Выберите платформу…
                                    </option>

                                    {
                                        platforms.filter(platform => platform.mode === "live").map(
                                            platform => (
                                                <option
                                                    key={
                                                        platform.id
                                                    }

                                                    value={
                                                        platform.id
                                                    }
                                                >
                                                    {
                                                        platformLabels[
                                                            platform.broker
                                                        ]
                                                        ?? platform.broker
                                                    }

                                                    {" · "}

                                                    {
                                                        modeLabels[
                                                            platform.mode
                                                        ]
                                                        ?? platform.mode
                                                    }
                                                </option>
                                            )
                                        )
                                    }
                                </select>

                                {
                                    platforms.length
                                    === 0
                                    && (
                                        <div
                                            style={{
                                                fontSize:
                                                    12,

                                                color:
                                                    "var(--text-muted)",

                                                marginTop:
                                                    4,
                                            }}
                                        >
                                            Сначала подключите платформу на вкладке «Настройки».
                                        </div>
                                    )
                                }
                            </label>
                        )
                    }

                    {form.broker !== "bybit" && <label>
                        ID брокерского счёта

                        <input
                            value={
                                form
                                    .brokerAccountId
                            }

                            onChange={
                                event =>
                                    setForm(
                                        previous => ({
                                            ...previous,

                                            brokerAccountId:
                                                event
                                                    .target
                                                    .value,
                                        })
                                    )
                            }

                            style={{
                                width:
                                    "100%",

                                marginTop:
                                    6,
                            }}
                        />
                    </label>}



                    {
                        form.broker
                        === "bybit"
                        && (
                            <label>
                                Основная валюта

                                <select
                                    value={
                                        form
                                            .baseCurrency
                                    }

                                    onChange={
                                        event =>
                                            setForm(
                                                previous => ({
                                                    ...previous,

                                                    baseCurrency:
                                                        event
                                                            .target
                                                            .value,
                                                })
                                            )
                                    }

                                    style={{
                                        width:
                                            "100%",

                                        marginTop:
                                            6,
                                    }}
                                >
                                    <option
                                        value="USDT"
                                    >
                                        USDT
                                    </option>

                                    <option
                                        value="USDC"
                                    >
                                        USDC
                                    </option>
                                </select>
                            </label>
                        )
                    }
                </div>

                {
                    editingId
                    !== null
                    && selectedBroker
                    && (
                        <div
                            style={{
                                marginTop:
                                18,

                                display:
                                "grid",

                                gridTemplateColumns:
                                "repeat(auto-fit, minmax(260px, 1fr))",

                                gap:
                                14,
                            }}
                        >
                            {
                                selectedBroker
                                .credential_fields
                                .map(
                                    field => (
                                        <label
                                            key={
                                                field.key
                                            }
                                        >
                                            {
                                                field.label
                                            }

                                            <input
                                                type={
                                                    field.type
                                                        === "password"
                                                        ? "password"
                                                        : "text"
                                                }

                                                value={
                                                    form
                                                        .credentials[
                                                    field.key
                                                    ]
                                                    ?? ""
                                                }

                                                onChange={
                                                    event =>
                                                        updateCredential(
                                                            field.key,

                                                            event
                                                                .target
                                                                .value,
                                                        )
                                                }

                                                placeholder="Оставьте пустым, чтобы не менять"

                                                style={{
                                                    width:
                                                    "100%",

                                                    marginTop:
                                                    6,
                                                }}
                                            />
                                        </label>
                                    )
                                )
                            }
                        </div>
                    )
                }

                {
                    editingId
                    === null
                    && form.broker !== "bybit"
                    && (
                        <div
                            style={{
                                marginTop:
                                18,
                            }}
                        >
                            <button
                                type="button"

                                onClick={
                                    loadPlatformAccounts
                                }

                                disabled={
                                    discovering
                                    || form
                                        .platformId
                                    === null
                                }
                            >
                                {
                                    discovering
                                        ? "Загрузка счетов..."
                                        : "Показать счета платформы"
                                }
                            </button>

                            {
                                platforms.length
                                > 0
                                && selectedPlatform
                                === undefined
                                && (
                                    <div
                                        style={{
                                            marginTop:
                                            10,

                                            fontSize:
                                            13,

                                            color:
                                            "var(--text-muted)",
                                        }}
                                    >
                                        Выберите платформу, чтобы загрузить доступные счета.
                                    </div>
                                )
                            }

                            {
                                discoveryError
                                && (
                                    <div
                                        style={{
                                            marginTop:
                                                10,

                                            padding:
                                                10,

                                            borderRadius:
                                                10,

                                            background:
                                                "var(--loss-soft)",

                                            color:
                                                "var(--loss)",

                                            wordBreak:
                                                "break-word",
                                        }}
                                    >
                                        {
                                            discoveryError
                                        }
                                    </div>
                                )
                            }

                            {
                                discovered
                                    .length
                                > 0
                                && (
                                    <div
                                        style={{
                                            marginTop:
                                                10,

                                            display:
                                                "grid",

                                            gap:
                                                8,
                                        }}
                                    >
                                        {
                                            discovered.map(
                                                account => {
                                                    const selected =
                                                        form
                                                            .brokerAccountId
                                                        === account
                                                            .broker_account_id

                                                    const alreadyAdded = (
                                                        account
                                                            .already_added
                                                        === true
                                                    )

                                                    return (
                                                        <button
                                                            key={
                                                                account
                                                                    .broker_account_id
                                                            }

                                                            type="button"

                                                            disabled={
                                                                alreadyAdded
                                                            }

                                                            onClick={
                                                                () =>
                                                                    selectDiscoveredAccount(
                                                                        account
                                                                    )
                                                            }

                                                            style={{
                                                                textAlign:
                                                                "left",

                                                                background:
                                                                selected
                                                                    ? "var(--profit-soft)"
                                                                    : "var(--card-soft)",

                                                                border:
                                                                    selected
                                                                        ? "1px solid #2f9e5f"
                                                                        : "1px solid var(--border)",

                                                                borderRadius:
                                                                12,

                                                                padding:
                                                                12,

                                                                opacity:
                                                                alreadyAdded
                                                                    ? 0.55
                                                                    : 1,

                                                                cursor:
                                                                alreadyAdded
                                                                    ? "default"
                                                                    : "pointer",
                                                            }}
                                                        >
                                                            <div>
                                                                <strong>
                                                                    {
                                                                        account
                                                                            .name
                                                                    }
                                                                </strong>

                                                                {" · "}

                                                                {
                                                                    account
                                                                        .account_type
                                                                }

                                                                {
                                                                    account
                                                                        .status
                                                                    === "1"
                                                                        ? " · активен"
                                                                        : ""
                                                                }

                                                                {
                                                                    alreadyAdded
                                                                        ? " · уже добавлен"
                                                                        : ""
                                                                }
                                                            </div>

                                                            <div
                                                                style={{
                                                                    opacity:
                                                                        0.65,

                                                                    fontSize:
                                                                        13,

                                                                    marginTop:
                                                                        4,
                                                                }}
                                                            >
                                                                ID:
                                                                {" "}

                                                                {
                                                                    account
                                                                        .broker_account_id
                                                                }
                                                            </div>

                                                            {
                                                                account
                                                                    .portfolio
                                                                && (
                                                                    <div
                                                                        style={{
                                                                            fontSize:
                                                                                13,

                                                                            marginTop:
                                                                                4,
                                                                        }}
                                                                    >
                                                                        Свободно:
                                                                        {" "}

                                                                        {
                                                                            formatMoney(
                                                                                account
                                                                                    .portfolio
                                                                                    .cash
                                                                            )
                                                                        }

                                                                        {" · "}

                                                                        Портфель:
                                                                        {" "}

                                                                        {
                                                                            formatMoney(
                                                                                account
                                                                                    .portfolio
                                                                                    .total_value
                                                                            )
                                                                        }

                                                                        {" · "}

                                                                        Позиций:
                                                                        {" "}

                                                                        {
                                                                            account
                                                                                .portfolio
                                                                                .positions_count
                                                                        }
                                                                    </div>
                                                                )
                                                            }
                                                        </button>
                                                    )
                                                }
                                            )
                                        }
                                    </div>
                                )
                            }
                        </div>
                    )
                }

                {form.broker !== "bybit" && <div
                    style={{
                        marginTop:
                            18,

                        display:
                            "grid",

                        gridTemplateColumns:
                            "repeat(auto-fit, minmax(220px, 1fr))",

                        gap:
                            14,
                    }}
                >
                    <label>
                        Комиссия

                        <select
                            value={
                                form
                                    .commissionMode
                            }

                            onChange={
                                event => {
                                    const commissionMode =
                                        event.target.value as CommissionMode

                                    setForm(
                                        previous => ({
                                            ...previous,

                                            commissionMode,
                                        })
                                    )
                                }
                            }

                            style={{
                                width:
                                    "100%",

                                marginTop:
                                    6,
                            }}
                        >
                            <option
                                value="auto"
                            >
                                Автоматически
                            </option>

                            <option
                                value="investor_030"
                            >
                                Инвестор — 0,30%
                            </option>

                            <option
                                value="trader_005"
                            >
                                Трейдер — 0,05%
                            </option>

                            <option
                                value="custom"
                            >
                                Пользовательская
                            </option>
                        </select>
                    </label>

                    {
                        form
                            .commissionMode
                        === "custom"
                        && (
                            <>
                                <label>
                                    BUY комиссия, %

                                    <input
                                        type=
                                        "number"

                                        min=
                                        "0"

                                        step=
                                        "0.01"

                                        value={
                                            form
                                                .customBuyCommission
                                        }

                                        onChange={
                                            event =>
                                                setForm(
                                                    previous => ({
                                                        ...previous,

                                                        customBuyCommission:
                                                            event
                                                                .target
                                                                .value,
                                                    })
                                                )
                                        }

                                        style={{
                                            width:
                                                "100%",

                                            marginTop:
                                                6,
                                        }}
                                    />
                                </label>

                                <label>
                                    SELL комиссия, %

                                    <input
                                        type=
                                        "number"

                                        min=
                                        "0"

                                        step=
                                        "0.01"

                                        value={
                                            form
                                                .customSellCommission
                                        }

                                        onChange={
                                            event =>
                                                setForm(
                                                    previous => ({
                                                        ...previous,

                                                        customSellCommission:
                                                            event
                                                                .target
                                                                .value,
                                                    })
                                                )
                                        }

                                        style={{
                                            width:
                                                "100%",

                                            marginTop:
                                                6,
                                        }}
                                    />
                                </label>
                            </>
                        )
                    }
                </div>}

                <label
                    style={{
                        display:
                            "flex",

                        gap:
                            8,

                        alignItems:
                            "center",

                        marginTop:
                            18,
                    }}
                >
                    <input
                        type=
                        "checkbox"

                        checked={
                            form.enabled
                        }

                     onChange={
                         event => {
                             setForm(
                                 previous => ({
                                     ...previous,

                                     enabled:
                                         event
                                             .target
                                             .checked,
                                 })
                             )
                         }
                     }
                 />

                    Счёт активен
                </label>

                {
                    error
                    && (
                        <div
                            style={{
                                marginTop:
                                    16,

                                padding:
                                    12,

                                borderRadius:
                                    10,

                                background:
                                    "var(--loss-soft)",

                                color:
                                    "var(--loss)",

                                wordBreak:
                                    "break-word",
                            }}
                        >
                            {
                                error
                            }
                        </div>
                    )
                }

                <button
                    type="button"

                    onClick={
                        saveAccount
                    }

                    disabled={
                        loading
                        || !form
                            .name
                            .trim()
                        || !form
                            .brokerAccountId
                            .trim()
                    }

                    style={{
                        marginTop:
                            18,

                        padding:
                            "10px 18px",
                    }}
                >
                    {
                        loading
                            ? "Сохранение..."
                            : editingId
                                ? "Сохранить изменения"
                                : "Добавить счёт"
                    }
                </button>
            </section>

            <section
                style={{
                    display:
                        "grid",

                    gap:
                        14,
                }}
            >
                <h2
                    style={{
                        marginBottom:
                            0,

                        fontSize:
                            20,
                    }}
                >
                    Торговые счета
                </h2>

                {
                    accounts.length
                    === 0
                    && (
                        <div>
                            Счета пока не добавлены.
                        </div>
                    )
                }

                {
                    accounts.map(
                        account => {
                            const broker =
                                brokers.find(
                                    item =>
                                        item.id
                                        === account
                                            .broker
                                )

                            const test =
                                connectionResult[
                                account.id
                                ]

                            const portfolio =
                                portfolios[
                                account.id
                                ]

                            return (
                                <article
                                    key={
                                        account.id
                                    }

                                    style={{
                                        background: "var(--card)",

                                        borderRadius:
                                            18,

                                        padding:
                                            18,

                                        boxShadow:
                                            "0 8px 28px rgba(0,0,0,0.06)",
                                    }}
                                >
                                    <div
                                        style={{
                                            display:
                                                "flex",

                                            alignItems:
                                                "center",

                                            gap:
                                                12,

                                            flexWrap:
                                                "wrap",
                                        }}
                                    >
                                        <div
                                            style={{
                                                width:
                                                    40,

                                                height:
                                                    40,

                                                borderRadius:
                                                    "50%",

                                                display:
                                                    "flex",

                                                alignItems:
                                                    "center",

                                                justifyContent:
                                                    "center",

                                                background:
                                                    account.enabled
                                                        ? "var(--accent)"
                                                        : "var(--card-soft)",

                                                color:
                                                    account.enabled
                                                        ? "#111111"
                                                        : "var(--text-muted)",

                                                fontWeight:
                                                    700,

                                                fontSize:
                                                    16,

                                                flexShrink:
                                                    0,
                                            }}
                                        >
                                            {
                                                (
                                                    account
                                                        .name
                                                        .trim()
                                                        .charAt(
                                                            0
                                                        )
                                                        .toUpperCase()

                                                    || "С"
                                                )
                                            }
                                        </div>

                                        <div
                                            style={{
                                                flex:
                                                    1,

                                                minWidth:
                                                    0,
                                            }}
                                        >
                                            <h3
                                                style={{
                                                    margin:
                                                        0,

                                                    fontSize:
                                                        16,
                                                }}
                                            >
                                                {
                                                    account
                                                        .name
                                                }
                                            </h3>

                                            <div
                                                style={{
                                                    marginTop:
                                                        2,

                                                    fontSize:
                                                        12,

                                                    color:
                                                        "var(--text-muted)",
                                                }}
                                            >
                                                {
                                                    broker
                                                        ?.name

                                                    ?? account
                                                        .broker
                                                }

                                                {" · "}

                                                {
                                                    account
                                                        .mode
                                                        === "live"
                                                        ? "LIVE"
                                                        : "SANDBOX"
                                                }
                                            </div>
                                        </div>

                                        <div
                                            style={{
                                                textAlign:
                                                    "right",
                                            }}
                                        >
                                            <div
                                                style={{
                                                    fontSize:
                                                        16,

                                                    fontWeight:
                                                        700,

                                                    color:
                                                        "var(--text)",
                                                }}
                                            >
                                                {
                                                    portfolio
                                                        ? formatMoney(
                                                            portfolio.total_value
                                                        )
                                                        : "—"
                                                }
                                            </div>

                                            <div
                                                style={{
                                                    marginTop:
                                                        2,

                                                    display:
                                                        "inline-flex",

                                                    alignItems:
                                                        "center",

                                                    gap:
                                                        4,

                                                    fontSize:
                                                        11,

                                                    color:
                                                        account.enabled
                                                            ? "var(--profit)"
                                                            : "var(--text-dim)",

                                                    background:
                                                        account.enabled
                                                            ? "var(--profit-soft)"
                                                            : "var(--card-soft)",

                                                    padding:
                                                        "2px 8px",

                                                    borderRadius:
                                                        999,
                                                }}
                                            >
                                                <span
                                                    style={{
                                                        width:
                                                            6,

                                                        height:
                                                            6,

                                                        borderRadius:
                                                            "50%",

                                                        background:
                                                            account.enabled
                                                                ? "var(--profit)"
                                                                : "var(--text-dim)",

                                                        display:
                                                            "inline-block",
                                                    }}
                                                />

                                                {
                                                    account
                                                        .enabled
                                                        ? "Активен"
                                                        : "Отключён"
                                                }
                                            </div>
                                        </div>
                                    </div>

                                    <div
                                        style={{
                                            marginTop:
                                                16,

                                            display:
                                                "grid",

                                            gridTemplateColumns:
                                                "repeat(auto-fit, minmax(180px, 1fr))",

                                            gap:
                                                12,
                                        }}
                                    >
                                        <div>
                                            <small>
                                                ID счёта
                                            </small>

                                            <div>
                                                {
                                                    account
                                                        .broker_account_id
                                                }
                                            </div>
                                        </div>

                                        <div>
                                            <small>
                                                Комиссия
                                            </small>

                                            <div>
                                                {
                                                    commissionLabel(
                                                        account
                                                            .commission_mode
                                                    )
                                                }
                                            </div>
                                        </div>

                                        <div>
                                            <small>
                                                BUY
                                            </small>

                                            <div>
                                                {
                                                    account
                                                        .expected_buy_commission_percent
                                                }
                                                %
                                            </div>
                                        </div>

                                        <div>
                                            <small>
                                                SELL
                                            </small>

                                            <div>
                                                {
                                                    account
                                                        .expected_sell_commission_percent
                                                }
                                                %
                                            </div>
                                        </div>

                                        {
                                            portfolio
                                            && (
                                                <>
                                                    <div>
                                                        <small>
                                                            Свободные средства
                                                        </small>

                                                        <div>
                                                            {
                                                                formatMoney(
                                                                    portfolio
                                                                        .cash
                                                                )
                                                            }
                                                        </div>
                                                    </div>

                                                    <div>
                                                        <small>
                                                            Стоимость портфеля
                                                        </small>

                                                        <div>
                                                            {
                                                                formatMoney(
                                                                    portfolio
                                                                        .total_value
                                                                )
                                                            }
                                                        </div>
                                                    </div>

                                                    <div>
                                                        <small>
                                                            Позиций
                                                        </small>

                                                        <div>
                                                            {
                                                                portfolio
                                                                    .positions_count
                                                            }
                                                        </div>
                                                    </div>
                                                </>
                                            )
                                        }
                                    </div>

                                    {
                                        test
                                        && (
                                            <div
                                                style={{
                                                    marginTop:
                                                        14,

                                                    padding:
                                                        10,

                                                    borderRadius:
                                                        10,

                                                    background:
                                                        (
                                                            test
                                                                .success
                                                            && test
                                                                .account_found
                                                        )
                                                            ? "var(--profit-soft)"
                                                            : "var(--loss-soft)",
                                                }}
                                            >
                                                {
                                                    (
                                                        test
                                                            .success
                                                        && test
                                                            .account_found
                                                    )
                                                        ? "Подключение успешно"
                                                        : (
                                                            test
                                                                .error
                                                            ?? "Счёт у брокера не найден"
                                                        )
                                                }
                                            </div>
                                        )
                                    }

                                    <AccountMovementsCard
                                        accountId={
                                            account.id
                                        }
                                    />

                                    <div
                                        style={{
                                            marginTop:
                                                16,

                                            display:
                                                "flex",

                                            gap:
                                                10,

                                            flexWrap:
                                                "wrap",
                                        }}
                                    >
                                        <button
                                            type="button"

                                            onClick={
                                                () =>
                                                    testConnection(
                                                        account
                                                    )
                                            }
                                        >
                                            Проверить подключение
                                        </button>

                                        <button
                                            type="button"

                                            onClick={
                                                () =>
                                                    editAccount(
                                                        account
                                                    )
                                            }
                                        >
                                            Изменить
                                        </button>

                                        <button
                                            type="button"

                                            onClick={
                                                () =>
                                                    removeAccount(
                                                        account
                                                    )
                                            }
                                        >
                                            Удалить
                                        </button>
                                    </div>
                                </article>
                            )
                        }
                    )
                }
            </section>
        </div>
    )
}
