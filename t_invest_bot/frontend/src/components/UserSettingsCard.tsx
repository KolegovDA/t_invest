import { useEffect, useState } from "react"

import {
    getCommissionSummary,
    getHeadHistory,
    getTopups,
    submitTopup,
    updateProfile,
    type AuthUser,
    type HeadHistoryResponse,
    type TopupRequest,
    type TopupsResponse,
} from "../api"
import type { CommissionSummary } from "../types"


function formatMoney(
    value: number | string | null
): string {
    if (
        value
        === null
        || value
        === undefined
    ) {
        return "—"
    }

    const num = (
        Number(
            value
        )
    )

    if (
        Number.isNaN(
            num
        )
    ) {
        return String(
            value
        )
    }

    return num
        .toLocaleString(
            "ru-RU",
            {
                maximumFractionDigits:
                    2,
            }
        )
}


function formatTime(
    value: string | null | undefined
): string {
    if (
        !value
    ) {
        return "—"
    }

    const ts = (
        Date.parse(
            value
        )
    )

    if (
        Number.isNaN(
            ts
        )
    ) {
        return value
    }

    return (
        new Date(
            ts
        )
        .toLocaleString(
            "ru-RU"
        )
    )
}


function payloadString(
    payload: Record<string, unknown>,
    key: string
): string | null {
    const value = (
        payload[
            key
        ]
    )

    if (
        value
        === null
        || value
        === undefined
    ) {
        return null
    }

    return String(
        value
    )
}


type Props = {
    user: AuthUser

    onUpdated: (
        user: AuthUser
    ) => void
}


export function UserSettingsCard({
    user,
    onUpdated,
}: Props) {
    const [
        editing,
        setEditing,
    ] = useState(
        false
    )

    const [
        saving,
        setSaving,
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
        fullName,
        setFullName,
    ] = useState(
        user.full_name
        ?? ""
    )

    const [
        phone,
        setPhone,
    ] = useState(
        user.phone
        ?? ""
    )

    const [
        email,
        setEmail,
    ] = useState(
        user.email
        ?? ""
    )

    const [
        birthDate,
        setBirthDate,
    ] = useState(
        user.birth_date
        ?? ""
    )

    const [
        history,
        setHistory,
    ] = useState<
        HeadHistoryResponse | null
    >(null)

    const [
        commission,
        setCommission,
    ] = useState<
        CommissionSummary | null
    >(null)

    const [
        topups,
        setTopups,
    ] = useState<
        TopupsResponse | null
    >(null)

    const [
        showTopupForm,
        setShowTopupForm,
    ] = useState(
        false
    )

    const [
        topupAmount,
        setTopupAmount,
    ] = useState(
        ""
    )

    const [
        topupComment,
        setTopupComment,
    ] = useState(
        ""
    )

    const [
        topupFile,
        setTopupFile,
    ] = useState<
        File | null
    >(null)

    const [
        topupSending,
        setTopupSending,
    ] = useState(
        false
    )

    const [
        topupError,
        setTopupError,
    ] = useState<
        string | null
    >(null)

    const [
        section,
        setSection,
    ] = useState<
        "data"
        | "history"
        | "balance"
    >(
        "balance"
    )

    useEffect(
        () => {
            setFullName(
                user.full_name
                ?? ""
            )

            setPhone(
                user.phone
                ?? ""
            )

            setEmail(
                user.email
                ?? ""
            )

            setBirthDate(
                user.birth_date
                ?? ""
            )
        },

        [user]
    )

    useEffect(
        () => {
            if (
                section
                === "history"
                && history
                === null
            ) {
                getHeadHistory(
                    10
                )
                    .then(
                        setHistory
                    )

                    .catch(
                        () => {
                            setHistory(
                                {
                                    available:
                                    false,

                                    syncs: [],
                                }
                            )
                        }
                    )
            }

            if (
                section
                === "balance"
                && commission
                === null
            ) {
                getCommissionSummary(
                    20
                )
                    .then(
                        setCommission
                    )

                    .catch(
                        () => {
                            setCommission(
                                null
                            )
                        }
                    )
            }

            if (
                section
                === "balance"
                && topups
                === null
            ) {
                getTopups(
                    20
                )
                    .then(
                        setTopups
                    )

                    .catch(
                        () => {
                            setTopups(
                                {
                                    available:
                                    false,

                                    requests: [],

                                    balance:
                                    "0",
                                }
                            )
                        }
                    )
            }
        },

        [section]
    )

    async function refreshBalance() {
        getCommissionSummary(
            20
        )
            .then(
                setCommission
            )

            .catch(
                () => {}
            )

        getTopups(
            20
        )
            .then(
                setTopups
            )

            .catch(
                () => {}
            )
    }

    async function sendTopup() {
        setTopupSending(
            true
        )

        setTopupError(
            null
        )

        try {
            await submitTopup(
                {
                    amount:
                    topupAmount,

                    comment:
                    topupComment,

                    document:
                    topupFile,
                }
            )

            setShowTopupForm(
                false
            )

            setTopupAmount(
                ""
            )

            setTopupComment(
                ""
            )

            setTopupFile(
                null
            )

            await refreshBalance()
        }
        catch (e) {
            setTopupError(
                e instanceof Error
                    ? e.message
                    : "Ошибка отправки заявки"
            )
        }
        finally {
            setTopupSending(
                false
            )
        }
    }

    async function save() {
        setSaving(
            true
        )

        setError(
            null
        )

        try {
            const data = (
                await updateProfile(
                    {
                        full_name:
                        fullName,

                        phone,

                        email,

                        birth_date:
                        birthDate,
                    }
                )
            )

            onUpdated(
                data.user
            )

            setEditing(
                false
            )
        }
        catch (e) {
            setError(
                e instanceof Error
                    ? e.message
                    : "Ошибка сохранения"
            )
        }
        finally {
            setSaving(
                false
            )
        }
    }

    return (
        <div
            style={{
                background:
                "var(--card)",

                borderRadius:
                16,

                padding:
                "16px 16px 14px",

                marginBottom:
                14,
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
                <b>
                    Пользователь
                </b>

                <div
                    style={{
                        display:
                        "flex",

                        gap:
                        6,
                    }}
                >
                    {(
                        [
                            "balance",

                            "data",

                            "history",
                        ] as const
                    )
                    .map(
                        key => (
                            <button
                                key={
                                    key
                                }

                                onClick={() => {
                                    setSection(
                                        key
                                    )
                                }}

                                style={{
                                    border:
                                    "none",

                                    background: (
                                        section
                                        === key
                                            ? "var(--accent-soft)"
                                            : "var(--card-soft)"
                                    ),

                                    color:
                                    "var(--text)",

                                    borderRadius:
                                    8,

                                    padding:
                                    "5px 10px",

                                    fontSize:
                                    12,

                                    cursor:
                                    "pointer",
                                }}
                            >
                                {
                                    key
                                    === "data"
                                        ? "Данные"
                                        : key
                                        === "history"
                                            ? "История"
                                            : "Баланс"
                                }
                            </button>
                        )
                    )}
                </div>
            </div>

            {
                section
                === "data"
                && (
                    editing
                        ? (
                            <div>
                                <label
                                    style={{
                                        display:
                                        "block",

                                        fontSize:
                                        12,

                                        color:
                                        "var(--text-muted)",

                                        marginTop:
                                        8,
                                    }}
                                >
                                    ФИО

                                    <input
                                        value={
                                            fullName
                                        }

                                        onChange={
                                            event => {
                                                setFullName(
                                                    event
                                                        .target
                                                        .value
                                                )
                                            }
                                        }

                                        style={{
                                            width:
                                            "100%",

                                            marginTop:
                                            4,

                                            padding:
                                            8,

                                            borderRadius:
                                            8,

                                            border:
                                            "1px solid var(--border)",

                                            background:
                                            "var(--bg)",

                                            color:
                                            "var(--text)",
                                        }}
                                    />
                                </label>

                                <label
                                    style={{
                                        display:
                                        "block",

                                        fontSize:
                                        12,

                                        color:
                                        "var(--text-muted)",

                                        marginTop:
                                        8,
                                    }}
                                >
                                    Телефон

                                    <input
                                        value={
                                            phone
                                        }

                                        onChange={
                                            event => {
                                                setPhone(
                                                    event
                                                        .target
                                                        .value
                                                )
                                            }
                                        }

                                        style={{
                                            width:
                                            "100%",

                                            marginTop:
                                            4,

                                            padding:
                                            8,

                                            borderRadius:
                                            8,

                                            border:
                                            "1px solid var(--border)",

                                            background:
                                            "var(--bg)",

                                            color:
                                            "var(--text)",
                                        }}
                                    />
                                </label>

                                <label
                                    style={{
                                        display:
                                        "block",

                                        fontSize:
                                        12,

                                        color:
                                        "var(--text-muted)",

                                        marginTop:
                                        8,
                                    }}
                                >
                                    Email

                                    <input
                                        value={
                                            email
                                        }

                                        onChange={
                                            event => {
                                                setEmail(
                                                    event
                                                        .target
                                                        .value
                                                )
                                            }
                                        }

                                        style={{
                                            width:
                                            "100%",

                                            marginTop:
                                            4,

                                            padding:
                                            8,

                                            borderRadius:
                                            8,

                                            border:
                                            "1px solid var(--border)",

                                            background:
                                            "var(--bg)",

                                            color:
                                            "var(--text)",
                                        }}
                                    />
                                </label>

                                <label
                                    style={{
                                        display:
                                        "block",

                                        fontSize:
                                        12,

                                        color:
                                        "var(--text-muted)",

                                        marginTop:
                                        8,
                                    }}
                                >
                                    Дата рождения

                                    <input
                                        value={
                                            birthDate
                                        }

                                        onChange={
                                            event => {
                                                setBirthDate(
                                                    event
                                                        .target
                                                        .value
                                                )
                                            }
                                        }

                                        style={{
                                            width:
                                            "100%",

                                            marginTop:
                                            4,

                                            padding:
                                            8,

                                            borderRadius:
                                            8,

                                            border:
                                            "1px solid var(--border)",

                                            background:
                                            "var(--bg)",

                                            color:
                                            "var(--text)",
                                        }}
                                    />
                                </label>

                                {
                                    error
                                    && (
                                        <div
                                            style={{
                                                marginTop:
                                                8,

                                                color:
                                                "var(--loss)",

                                                fontSize:
                                                13,
                                            }}
                                        >
                                            {
                                                error
                                            }
                                        </div>
                                    )
                                }

                                <button
                                    onClick={
                                        save
                                    }

                                    disabled={
                                        saving
                                        || !fullName
                                            .trim()
                                    }

                                    style={{
                                        marginTop:
                                        12,

                                        padding:
                                        "8px 16px",

                                        borderRadius:
                                        10,

                                        border:
                                        "none",

                                        background:
                                        "var(--accent)",

                                        color:
                                        "#111111",

                                        fontWeight:
                                        700,

                                        cursor:
                                        "pointer",
                                    }}
                                >
                                    {
                                        saving
                                            ? "Сохранение..."
                                            : "Сохранить"
                                    }
                                </button>
                            </div>
                        )
                        : (
                            <div
                                style={{
                                    fontSize:
                                    13,

                                    lineHeight:
                                    1.7,
                                }}
                            >
                                <div>
                                    <b>
                                        {
                                            user
                                                .full_name
                                        }
                                    </b>
                                </div>

                                <div
                                    style={{
                                        color:
                                        "var(--text-muted)",
                                    }}
                                >
                                    Логин: {
                                        user.login
                                    }
                                </div>

                                <div
                                    style={{
                                        color:
                                        "var(--text-muted)",
                                    }}
                                >
                                    Телефон: {
                                        user.phone
                                        ?? "—"
                                    }
                                </div>

                                <div
                                    style={{
                                        color:
                                        "var(--text-muted)",
                                    }}
                                >
                                    Email: {
                                        user.email
                                        ?? "—"
                                    }
                                </div>

                                <div
                                    style={{
                                        color:
                                        "var(--text-muted)",
                                    }}
                                >
                                    Дата рождения: {
                                        user.birth_date
                                        ?? "—"
                                    }
                                </div>

                                <button
                                    onClick={() => {
                                        setEditing(
                                            true
                                        )
                                    }}

                                    style={{
                                        marginTop:
                                        8,

                                        padding:
                                        "6px 14px",

                                        borderRadius:
                                        10,

                                        border:
                                        "none",

                                        background:
                                        "var(--card-soft)",

                                        color:
                                        "var(--text)",

                                        cursor:
                                        "pointer",
                                    }}
                                >
                                    Редактировать
                                </button>
                            </div>
                        )
                )
            }

            {
                section
                === "history"
                && (
                    <div>
                        {
                            history
                            === null
                                ? (
                                    <div
                                        style={{
                                            fontSize:
                                            13,

                                            color:
                                            "var(--text-muted)",
                                        }}
                                    >
                                        Загрузка...
                                    </div>
                                )
                                : !history.available
                                    ? (
                                        <div
                                            style={{
                                                fontSize:
                                                13,

                                                color:
                                                "var(--text-muted)",
                                            }}
                                        >
                                            Головной сервер недоступен или синхронизаций ещё не было.
                                        </div>
                                    )
                                    : (
                                        <div
                                            style={{
                                                fontSize:
                                                12,
                                            }}
                                        >
                                            {
                                                history
                                                .syncs
                                                .map(
                                                    sync => {
                                                        const balance = (
                                                            payloadString(
                                                                sync.payload,
                                                                "current_balance"
                                                            )
                                                        )

                                                        const profit = (
                                                            payloadString(
                                                                sync.payload,
                                                                "total_profit"
                                                            )
                                                        )

                                                        return (
                                                            <div
                                                                key={
                                                                    sync.id
                                                                }

                                                                style={{
                                                                    display:
                                                                    "flex",

                                                                    justifyContent:
                                                                    "space-between",

                                                                    padding:
                                                                    "6px 0",

                                                                    borderBottom:
                                                                    "1px solid var(--border)",
                                                                }}
                                                            >
                                                                <span
                                                                    style={{
                                                                        color:
                                                                        "var(--text-muted)",
                                                                    }}
                                                                >
                                                                    {
                                                                        formatTime(
                                                                            sync.created_at
                                                                        )
                                                                    }
                                                                </span>

                                                                <span>
                                                                    {
                                                                        formatMoney(
                                                                            balance
                                                                        )
                                                                    }

                                                                    {" · "}

                                                                    {
                                                                        formatMoney(
                                                                            profit
                                                                        )
                                                                    }
                                                                </span>
                                                            </div>
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

            {
                section
                === "balance"
                && (
                    <div>
                        <div
                            style={{
                                display:
                                "flex",

                                justifyContent:
                                "space-between",

                                alignItems:
                                "baseline",

                                marginBottom:
                                6,
                            }}
                        >
                            <span
                                style={{
                                    color:
                                    "var(--text-muted)",

                                    fontSize:
                                    13,
                                }}
                            >
                                Баланс клиентского счёта
                            </span>

                            <b
                                style={{
                                    fontSize:
                                    16,
                                }}
                            >
                                {
                                    formatMoney(
                                        commission
                                        ?.balance
                                        ?? topups
                                        ?.balance
                                        ?? null
                                    )
                                }

                                {" ₽"}
                            </b>
                        </div>

                        <div
                            style={{
                                display:
                                "flex",

                                gap:
                                6,

                                marginBottom:
                                10,
                            }}
                        >
                            <button
                                onClick={() => {
                                    setShowTopupForm(
                                        !showTopupForm
                                    )

                                    setTopupError(
                                        null
                                    )
                                }}

                                disabled={
                                    topupSending
                                }

                                style={{
                                    padding:
                                    "6px 14px",

                                    borderRadius:
                                    10,

                                    border:
                                    "none",

                                    background:
                                    "var(--accent)",

                                    color:
                                    "#111111",

                                    fontWeight:
                                    700,

                                    cursor:
                                    "pointer",
                                }}
                            >
                                Пополнить баланс
                            </button>

                            <button
                                onClick={
                                    refreshBalance
                                }

                                disabled={
                                    topupSending
                                }

                                style={{
                                    padding:
                                    "6px 14px",

                                    borderRadius:
                                    10,

                                    border:
                                    "none",

                                    background:
                                    "var(--card-soft)",

                                    color:
                                    "var(--text)",

                                    cursor:
                                    "pointer",
                                }}
                            >
                                Обновить
                            </button>
                        </div>

                        {
                            showTopupForm
                            && (
                                <div
                                    style={{
                                        marginBottom:
                                        12,
                                    }}
                                >
                                    <label
                                        style={{
                                            display:
                                            "block",

                                            fontSize:
                                            12,

                                            color:
                                            "var(--text-muted)",

                                            marginTop:
                                            8,
                                        }}
                                    >
                                        Сумма, ₽

                                        <input
                                            value={
                                                topupAmount
                                            }

                                            onChange={
                                                event => {
                                                    setTopupAmount(
                                                        event
                                                            .target
                                                            .value
                                                    )
                                                }
                                            }

                                            inputMode={
                                                "decimal" as const
                                            }

                                            placeholder={
                                                "10000"
                                            }

                                            style={{
                                                width:
                                                "100%",

                                                marginTop:
                                                4,

                                                padding:
                                                8,

                                                borderRadius:
                                                8,

                                                border:
                                                "1px solid var(--border)",

                                                background:
                                                "var(--bg)",

                                                color:
                                                "var(--text)",
                                            }}
                                        />
                                    </label>

                                    <label
                                        style={{
                                            display:
                                            "block",

                                            fontSize:
                                            12,

                                            color:
                                            "var(--text-muted)",

                                            marginTop:
                                            8,
                                        }}
                                    >
                                        Комментарий

                                        <input
                                            value={
                                                topupComment
                                            }

                                            onChange={
                                                event => {
                                                    setTopupComment(
                                                        event
                                                            .target
                                                            .value
                                                    )
                                                }
                                            }

                                            placeholder={
                                                "Необязательно"
                                            }

                                            style={{
                                                width:
                                                "100%",

                                                marginTop:
                                                4,

                                                padding:
                                                8,

                                                borderRadius:
                                                8,

                                                border:
                                                "1px solid var(--border)",

                                                background:
                                                "var(--bg)",

                                                color:
                                                "var(--text)",
                                            }}
                                        />
                                    </label>

                                    <label
                                        style={{
                                            display:
                                            "block",

                                            fontSize:
                                            12,

                                            color:
                                            "var(--text-muted)",

                                            marginTop:
                                            8,
                                        }}
                                    >
                                        Документ или фото

                                        <input
                                            type="file"

                                            accept={
                                                "image/*,.pdf"
                                            }

                                            onChange={
                                                event => {
                                                    setTopupFile(
                                                        event
                                                            .target
                                                            .files
                                                            ?.[0]
                                                        ?? null
                                                    )
                                                }
                                            }

                                            style={{
                                                width:
                                                "100%",

                                                marginTop:
                                                4,

                                                padding:
                                                6,

                                                borderRadius:
                                                8,

                                                border:
                                                "1px solid var(--border)",

                                                background:
                                                "var(--bg)",

                                                color:
                                                "var(--text)",
                                            }}
                                        />
                                    </label>

                                    {
                                        topupError
                                        && (
                                            <div
                                                style={{
                                                    marginTop:
                                                    8,

                                                    color:
                                                    "var(--loss)",

                                                    fontSize:
                                                    13,
                                                }}
                                            >
                                                {
                                                    topupError
                                                }
                                            </div>
                                        )
                                    }

                                    <button
                                        onClick={
                                            sendTopup
                                        }

                                        disabled={
                                            topupSending
                                            || !topupAmount
                                                .trim()
                                        }

                                        style={{
                                            marginTop:
                                            10,

                                            padding:
                                            "8px 16px",

                                            borderRadius:
                                            10,

                                            border:
                                            "none",

                                            background:
                                            "var(--accent)",

                                            color:
                                            "#111111",

                                            fontWeight:
                                            700,

                                            cursor:
                                            "pointer",
                                        }}
                                    >
                                        {
                                            topupSending
                                                ? "Отправка..."
                                                : "Отправить заявку"
                                        }
                                    </button>

                                    <div
                                        style={{
                                            marginTop:
                                            8,

                                            fontSize:
                                            12,

                                            color:
                                            "var(--text-muted)",
                                        }}
                                    >
                                        Заявка уйдёт на головной сервер. После подтверждения администратором баланс пополнится и придёт уведомление.
                                    </div>
                                </div>
                            )
                        }

                        {
                            (
                                topups
                                ?.requests
                                .length
                                ?? 0
                            )
                            > 0
                            && (
                                <div
                                    style={{
                                        fontSize:
                                        12,

                                        marginBottom:
                                        10,
                                    }}
                                >
                                    <div
                                        style={{
                                            color:
                                            "var(--text-muted)",

                                            marginBottom:
                                            4,
                                        }}
                                    >
                                        Заявки на пополнение
                                    </div>

                                    {
                                        topups
                                        ?.requests
                                        .map(
                                            (
                                                request,
                                            ) => {
                                                const statusColor = (
                                                    request
                                                    .status
                                                    === "approved"
                                                        ? "var(--profit)"
                                                        : request
                                                        .status
                                                        === "rejected"
                                                            ? "var(--loss)"
                                                            : "var(--accent)"
                                                )

                                                const statusLabel = (
                                                    request
                                                    .status
                                                    === "approved"
                                                        ? "подтверждена"
                                                        : request
                                                        .status
                                                        === "rejected"
                                                            ? "отклонена"
                                                            : "ожидает подтверждения"
                                                )

                                                return (
                                                    <div
                                                        key={
                                                            request
                                                            .id
                                                        }

                                                        style={{
                                                            display:
                                                            "flex",

                                                            justifyContent:
                                                            "space-between",

                                                            padding:
                                                            "6px 0",

                                                            borderBottom:
                                                            "1px solid var(--border)",
                                                        }}
                                                    >
                                                        <span
                                                            style={{
                                                                color:
                                                                "var(--text-muted)",
                                                            }}
                                                        >
                                                            {
                                                                formatTime(
                                                                    request
                                                                    .created_at
                                                                )
                                                            }

                                                            {" · "}

                                                            {
                                                                formatMoney(
                                                                    request
                                                                    .amount
                                                                )
                                                            }

                                                            {" ₽"}

                                                            {
                                                                request
                                                                .review_note
                                                                ? ` · ${request.review_note}`
                                                                : ""
                                                            }
                                                        </span>

                                                        <span
                                                            style={{
                                                                color: (
                                                                    statusColor
                                                                ),
                                                            }}
                                                        >
                                                            {
                                                                statusLabel
                                                            }
                                                        </span>
                                                    </div>
                                                )
                                            }
                                        )
                                    }
                                </div>
                            )
                        }

                        {
                            (
                                commission
                                ?.charges
                                .length
                                ?? 0
                            )
                            === 0
                                ? (
                                    <div
                                        style={{
                                            fontSize:
                                            13,

                                            color:
                                            "var(--text-muted)",
                                        }}
                                    >
                                        Списаний и пополнений пока нет.
                                    </div>
                                )
                                : (
                                    <div
                                        style={{
                                            fontSize:
                                            12,
                                        }}
                                    >
                                        {
                                            commission
                                            ?.charges
                                            .map(
                                                charge => {
                                                    const amount = (
                                                        Number(
                                                            charge.amount
                                                        )
                                                    )

                                                    const label = (
                                                        charge
                                                        .broker
                                                        === "topup"
                                                            ? "Пополнение"
                                                            : charge.ticker
                                                            ?? "—"
                                                    )

                                                    return (
                                                        <div
                                                            key={
                                                                charge.id
                                                            }

                                                            style={{
                                                                display:
                                                                "flex",

                                                                justifyContent:
                                                                "space-between",

                                                                padding:
                                                                "6px 0",

                                                                borderBottom:
                                                                "1px solid var(--border)",
                                                            }}
                                                        >
                                                            <span
                                                                style={{
                                                                    color:
                                                                    "var(--text-muted)",
                                                                }}
                                                            >
                                                                {
                                                                    formatTime(
                                                                        charge.created_at
                                                                    )
                                                                }

                                                                {" · "}

                                                                {
                                                                    label
                                                                }
                                                            </span>

                                                            <span
                                                                style={{
                                                                    color: (
                                                                        amount
                                                                        >= 0
                                                                            ? "var(--profit)"
                                                                            : "var(--loss)"
                                                                    ),
                                                                }}
                                                            >
                                                                {
                                                                    formatMoney(
                                                                        charge.amount
                                                                    )
                                                                }

                                                                {" → "}

                                                                {
                                                                    formatMoney(
                                                                        charge.balance_after
                                                                    )
                                                                }
                                                            </span>
                                                        </div>
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
        </div>
    )
}
