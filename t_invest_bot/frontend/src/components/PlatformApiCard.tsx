import {
    useEffect,
    useState,
} from "react"

import {
    createPlatform,
    deletePlatform,
    getBrokers,
    getPlatforms,
    updatePlatformCredentials,
} from "../accounts/api"

import type {
    BrokerInfo,
    BrokerType,
    PlatformConnection,
    TradingAccountMode,
} from "../accounts/types"

import { AppModal } from "./AppModal"


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


export function PlatformApiCard() {
    const [
        platforms,
        setPlatforms,
    ] = useState<
        PlatformConnection[]
    >([])

    const [
        brokers,
        setBrokers,
    ] = useState<
        BrokerInfo[]
    >([])

    const [
        modalOpen,
        setModalOpen,
    ] = useState(
        false
    )

    const [
        editingPlatform,
        setEditingPlatform,
    ] = useState<
        PlatformConnection | null
    >(null)

    const [
        broker,
        setBroker,
    ] = useState<BrokerType>(
        "tinvest"
    )

    const [
        mode,
        setMode,
    ] = useState<TradingAccountMode>(
        "live"
    )

    const [
        credentials,
        setCredentials,
    ] = useState<
        Record<
            string,
            string
        >
    >({})

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


    async function reload() {
        const [
            loadedPlatforms,
            loadedBrokers,
        ] = await Promise.all([
            getPlatforms(),
            getBrokers(),
        ])

        setPlatforms(
            loadedPlatforms
        )

        setBrokers(
            loadedBrokers
        )
    }


    useEffect(
        () => {
            reload()
                .catch(
                    currentError => {
                        setError(
                            currentError instanceof Error
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


    const selectedBroker =
        brokers.find(
            item =>
                item.id
                === broker
        )



    function isTaken(
        brokerId: string,

        modeValue: string
    ) {
        return (
            platforms.some(
                platform => (
                    platform
                        .broker
                    === brokerId

                    && platform
                        .mode
                    === modeValue
                )
            )
        )
    }


    function openAdd() {
        setEditingPlatform(
            null
        )

        const firstBroker = (
            brokers.find(
                item => (
                    item
                        .supported
                )
            )
        )

        setBroker(
            firstBroker
                ?.id
                ?? "tinvest"
        )

        setMode(
            "live"
        )

        setCredentials(
            {}
        )

        setError(
            null
        )

        setModalOpen(
            true
        )
    }


    function openEdit(
        platform: PlatformConnection
    ) {
        setEditingPlatform(
            platform
        )

        setBroker(
            platform
                .broker
        )

        setMode(
            platform
                .mode
        )

        setCredentials(
            {}
        )

        setError(
            null
        )

        setModalOpen(
            true
        )
    }


    function updateCredential(
        key: string,

        value: string
    ) {
        setCredentials(
            previous => ({
                ...previous,

                [key]:
                    value,
            })
        )
    }


    async function savePlatform() {
        const filled = (
            Object.fromEntries(
                Object.entries(
                    credentials
                )
                .filter(
                    ([, value]) =>
                        value
                            .trim()
                        !== ""
                )
            )
        )

        if (
            Object.keys(
                filled
            ).length
            === 0
        ) {
            setError(
                "Укажите ключи доступа платформы"
            )

            return
        }

        setSaving(
            true
        )

        setError(
            null
        )

        try {
            if (
                editingPlatform
            ) {
                await updatePlatformCredentials(
                    editingPlatform
                        .id,

                    filled
                )

            } else {
                await createPlatform({
                    broker,

                    mode,

                    credentials:
                        filled,
                })
            }

            await reload()

            setModalOpen(
                false
            )

        } catch (
        currentError
        ) {
            setError(
                currentError instanceof Error
                    ? currentError.message
                    : String(
                        currentError
                    )
            )

        } finally {
            setSaving(
                false
            )
        }
    }


    async function removePlatform(
        platform: PlatformConnection
    ) {
        const accepted = (
            window.confirm(
                `Отключить платформу "${platformLabels[platform.broker] ?? platform.broker} (${modeLabels[platform.mode] ?? platform.mode})"?`
            )
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

            await deletePlatform(
                platform
                    .id
            )

            await reload()

        } catch (
        currentError
        ) {
            setError(
                currentError instanceof Error
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
                    Платформы
                </b>

                <button
                    onClick={
                        openAdd
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

                        fontSize:
                        13,
                    }}
                >
                    + Добавить
                </button>
            </div>

            {
                error
                && (
                    <div
                        style={{
                            fontSize:
                            13,

                            color:
                            "var(--loss)",

                            marginBottom:
                            10,

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

            {
                platforms
                .length
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
                        Платформы не подключены. Нажмите «Добавить», чтобы подключить брокера и указать ключи доступа.
                    </div>
                )
                : (
                    platforms
                    .map(
                        platform => (
                            <div
                                key={
                                    platform
                                        .id
                                }

                                style={{
                                    display:
                                    "flex",

                                    justifyContent:
                                    "space-between",

                                    alignItems:
                                    "center",

                                    gap:
                                    10,

                                    padding:
                                    "8px 0",

                                    borderBottom:
                                    "1px solid var(--border)",
                                }}
                            >
                                <div>
                                    <b
                                        style={{
                                            fontSize:
                                            14,
                                        }}
                                    >
                                        {
                                            platformLabels[
                                                platform
                                                    .broker
                                            ]
                                            ?? platform
                                                .broker
                                        }

                                        {" · "}

                                        {
                                            modeLabels[
                                                platform
                                                    .mode
                                            ]
                                            ?? platform
                                                .mode
                                        }
                                    </b>

                                    <div
                                        style={{
                                            fontSize:
                                            12,

                                            color:
                                            "var(--text-muted)",
                                        }}
                                    >
                                        Ключи доступа сохранены
                                    </div>
                                </div>

                                <div
                                    style={{
                                        display:
                                        "flex",

                                        gap:
                                        6,
                                    }}
                                >
                                    <button
                                        onClick={() =>
                                            openEdit(
                                                platform
                                            )
                                        }

                                        style={{
                                            padding:
                                            "5px 10px",

                                            borderRadius:
                                            10,

                                            border:
                                            "none",

                                            background:
                                            "var(--card-soft)",

                                            cursor:
                                            "pointer",

                                            fontSize:
                                            12,
                                        }}
                                    >
                                        Ключи
                                    </button>

                                    <button
                                        onClick={() =>
                                            removePlatform(
                                                platform
                                            )
                                        }

                                        style={{
                                            padding:
                                            "5px 10px",

                                            borderRadius:
                                            10,

                                            border:
                                            "none",

                                            background:
                                            "var(--loss-soft)",

                                            color:
                                            "var(--loss)",

                                            cursor:
                                            "pointer",

                                            fontSize:
                                            12,
                                        }}
                                    >
                                        Удалить
                                    </button>
                                </div>
                            </div>
                        )
                    )
                )
            }

            {
                modalOpen
                && (
                    <AppModal
                        title={
                            editingPlatform
                                ? "Ключи платформы"
                                : "Подключение платформы"
                        }

                        onClose={() => {
                            setModalOpen(
                                false
                            )
                        }}
                    >
                        <div
                            style={{
                                display:
                                "grid",

                                gap:
                                14,
                            }}
                        >
                            {
                                !(
                                    editingPlatform
                                )
                                && (
                                    <>
                                        <label>
                                            Платформа

                                            <select
                                                value={
                                                    broker
                                                }

                                                onChange={
                                                    event => {
                                                        const nextBroker = (
                                                            event.target.value as BrokerType
                                                        )

                                                        setBroker(
                                                            nextBroker
                                                        )

                                                        setCredentials(
                                                            {}
                                                        )

                                                        setMode("live")
                                                    }
                                                }

                                                style={{
                                                    width:
                                                    "100%",

                                                    marginTop:
                                                    6,
                                                }}
                                            >
                                                {
                                                    brokers
                                                    .filter(
                                                        item => (
                                                            item
                                                                .supported
                                                        )
                                                    )
                                                    .map(
                                                        item => (
                                                            <option
                                                                key={
                                                                    item.id
                                                                }

                                                                value={
                                                                    item.id
                                                                }
                                                            >
                                                                {
                                                                    item.name
                                                                }
                                                            </option>
                                                        )
                                                    )
                                                }
                                            </select>
                                        </label>


                                    </>
                                )
                            }

                            {
                                selectedBroker
                                ?.credential_fields
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
                                                    credentials[
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

                                                placeholder={
                                                    editingPlatform
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

                            {
                                error
                                && (
                                    <div
                                        style={{
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
                                            error
                                        }
                                    </div>
                                )
                            }

                            <button
                                onClick={
                                    savePlatform
                                }

                                disabled={
                                    saving
                                }
                            >
                                {
                                    saving
                                        ? "Сохранение..."
                                        : editingPlatform
                                            ? "Сохранить ключи"
                                            : "Подключить платформу"
                                }
                            </button>
                        </div>
                    </AppModal>
                )
            }
        </div>
    )
}
