import {
    useEffect,
    useMemo,
    useState,
} from "react"

import {
    createTradingAccount,
    deleteTradingAccount,
    getBrokers,
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
    TradingAccount,
    TradingAccountMode,
} from "./types"


type FormState = {
    name: string

    broker: string

    brokerAccountId: string

    mode: TradingAccountMode

    commissionMode:
    CommissionMode

    customBuyCommission: string

    customSellCommission: string

    credentials:
    Record<string, string>

    enabled: boolean
}


const emptyForm:
    FormState = {
    name: "",

    broker: "tinvest",

    brokerAccountId: "",

    mode: "live",

    commissionMode:
        "auto",

    customBuyCommission:
        "0.30",

    customSellCommission:
        "0.30",

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
    ] = useState(false)

    const [
        error,
        setError,
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

    async function reload() {
        const [
            loadedBrokers,
            loadedAccounts,
        ] = await Promise.all([
            getBrokers(),
            getTradingAccounts(),
        ])

        setBrokers(
            loadedBrokers
        )

        setAccounts(
            loadedAccounts
        )
    }

    useEffect(
        () => {
            reload()
                .catch(
                    currentError => {
                        setError(
                            String(
                                currentError
                            )
                        )
                    }
                )
        },
        []
    )

    function resetForm() {
        setForm(
            emptyForm
        )

        setEditingId(
            null
        )

        setError(
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
                                value.trim()
                                !== ""
                        )
                )

            if (
                editingId
                === null
                && Object.keys(
                    credentials
                ).length === 0
            ) {
                throw new Error(
                    "Укажите реквизиты доступа к брокеру"
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
                        form.broker
                        as CreateTradingAccountPayload[
                        "broker"
                    ],

                    broker_account_id:
                        form
                            .brokerAccountId,

                    credentials,

                    mode:
                        form.mode,

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
                const payload: any = {
                    name:
                        form.name,

                    broker_account_id:
                        form
                            .brokerAccountId,

                    mode:
                        form.mode,

                    commission_mode:
                        form
                            .commissionMode,

                    enabled:
                        form.enabled,
                }

                if (
                    Object.keys(
                        credentials
                    ).length > 0
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

            broker:
                account.broker,

            brokerAccountId:
                account
                    .broker_account_id,

            mode:
                account.mode,

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

            #
            # Старые credentials
            # никогда не возвращаются
            # с backend.
            #
            credentials: {},

            enabled:
                account.enabled,
        })

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

        if (!accepted) {
            return
        }

        try {
            await deleteTradingAccount(
                account.id
            )

            await reload()

        } catch (
        currentError
        ) {
            setError(
                String(
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
                display: "grid",
                gap: 20,
            }}
        >
            <section
                style={{
                    background: "#ffffff",
                    borderRadius: 18,
                    padding: 20,
                    boxShadow:
                        "0 8px 28px rgba(0,0,0,0.06)",
                }}
            >
                <div
                    style={{
                        display: "flex",
                        justifyContent:
                            "space-between",
                        gap: 16,
                        alignItems:
                            "center",
                        marginBottom: 18,
                    }}
                >
                    <div>
                        <h2
                            style={{
                                margin: 0,
                            }}
                        >
                            {
                                editingId
                                    ? "Редактирование счёта"
                                    : "Добавить торговый счёт"
                            }
                        </h2>

                        <div
                            style={{
                                marginTop: 6,
                                opacity: 0.65,
                            }}
                        >
                            ESM Trade System 1.1
                        </div>
                    </div>

                    {
                        editingId
                        && (
                            <button
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
                        display: "grid",
                        gridTemplateColumns:
                            "repeat(auto-fit, minmax(220px, 1fr))",
                        gap: 14,
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
                            placeholder="Основной счёт"
                            style={{
                                width: "100%",
                                marginTop: 6,
                            }}
                        />
                    </label>

                    <label>
                        Брокер

                        <select
                            value={
                                form.broker
                            }
                            disabled={
                                editingId
                                !== null
                            }
                            onChange={
                                event => {
                                    setForm(
                                        previous => ({
                                            ...previous,

                                            broker:
                                                event
                                                    .target
                                                    .value,

                                            credentials:
                                                {},
                                        })
                                    )
                                }
                            }
                            style={{
                                width: "100%",
                                marginTop: 6,
                            }}
                        >
                            {
                                brokers.map(
                                    broker => (
                                        <option
                                            key={
                                                broker.id
                                            }
                                            value={
                                                broker.id
                                            }
                                            disabled={
                                                !broker
                                                    .supported
                                            }
                                        >
                                            {
                                                broker
                                                    .name
                                            }
                                            {
                                                !broker
                                                    .supported
                                                    ? " — скоро"
                                                    : ""
                                            }
                                        </option>
                                    )
                                )
                            }
                        </select>
                    </label>

                    <label>
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
                                width: "100%",
                                marginTop: 6,
                            }}
                        />
                    </label>

                    <label>
                        Режим

                        <select
                            value={
                                form.mode
                            }
                            onChange={
                                event =>
                                    setForm(
                                        previous => ({
                                            ...previous,

                                            mode:
                                                event
                                                    .target
                                                    .value
                                                as TradingAccountMode,
                                        })
                                    )
                            }
                            style={{
                                width: "100%",
                                marginTop: 6,
                            }}
                        >
                            {
                                (
                                    selectedBroker
                                        ?.modes
                                    ?? [
                                        "live",
                                    ]
                                ).map(
                                    mode => (
                                        <option
                                            key={
                                                mode
                                            }
                                            value={
                                                mode
                                            }
                                        >
                                            {
                                                mode
                                                    === "live"
                                                    ? "Боевой"
                                                    : "Песочница"
                                            }
                                        </option>
                                    )
                                )
                            }
                        </select>
                    </label>
                </div>

                {
                    selectedBroker
                    && (
                        <div
                            style={{
                                marginTop: 18,
                                display: "grid",
                                gridTemplateColumns:
                                    "repeat(auto-fit, minmax(260px, 1fr))",
                                gap: 14,
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
                                                                    .value
                                                            )
                                                    }
                                                    placeholder={
                                                        editingId
                                                            ? "Оставьте пустым, чтобы не менять"
                                                            : ""
                                                    }
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

                <div
                    style={{
                        marginTop: 18,
                        display: "grid",
                        gridTemplateColumns:
                            "repeat(auto-fit, minmax(220px, 1fr))",
                        gap: 14,
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
                                event =>
                                    setForm(
                                        previous => ({
                                            ...previous,

                                            commissionMode:
                                                event
                                                    .target
                                                    .value
                                                as CommissionMode,
                                        })
                                    )
                            }
                            style={{
                                width: "100%",
                                marginTop: 6,
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
                                        type="number"
                                        step="0.01"
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
                                        type="number"
                                        step="0.01"
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
                </div>

                <label
                    style={{
                        display: "flex",
                        gap: 8,
                        alignItems:
                            "center",
                        marginTop: 18,
                    }}
                >
                    <input
                        type="checkbox"
                        checked={
                            form.enabled
                        }
                        onChange={
                            event =>
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
                    />

                    Счёт активен
                </label>

                {
                    error
                    && (
                        <div
                            style={{
                                marginTop: 16,
                                padding: 12,
                                borderRadius: 10,
                                background:
                                    "#fff1f1",
                            }}
                        >
                            {error}
                        </div>
                    )
                }

                <button
                    onClick={
                        saveAccount
                    }
                    disabled={
                        loading
                        || !form.name
                        || !form
                            .brokerAccountId
                    }
                    style={{
                        marginTop: 18,
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
                    display: "grid",
                    gap: 14,
                }}
            >
                <h2
                    style={{
                        marginBottom: 0,
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
                                        background:
                                            "#ffffff",
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
                                            justifyContent:
                                                "space-between",
                                            gap: 16,
                                            flexWrap:
                                                "wrap",
                                        }}
                                    >
                                        <div>
                                            <h3
                                                style={{
                                                    margin:
                                                        0,
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
                                                        6,
                                                    opacity:
                                                        0.65,
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

                                        <div>
                                            {
                                                account
                                                    .enabled
                                                    ? "Активен"
                                                    : "Отключён"
                                            }
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
                                            gap: 12,
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
                                                            test.success
                                                            && test
                                                                .account_found
                                                        )
                                                            ? "#effaf2"
                                                            : "#fff1f1",
                                                }}
                                            >
                                                {
                                                    (
                                                        test.success
                                                        && test
                                                            .account_found
                                                    )
                                                        ? "Подключение успешно"
                                                        : (
                                                            test.error
                                                            ?? "Счёт у брокера не найден"
                                                        )
                                                }
                                            </div>
                                        )
                                    }

                                    <div
                                        style={{
                                            marginTop:
                                                16,
                                            display:
                                                "flex",
                                            gap: 10,
                                            flexWrap:
                                                "wrap",
                                        }}
                                    >
                                        <button
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
