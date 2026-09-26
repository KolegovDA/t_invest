import {
    useState,
} from "react"

import {
    getPhantoms,
    resolvePhantoms,
} from "../api"

import type {
    PhantomEntry,
} from "../types"


function entryKey(
    entry: PhantomEntry
): string {
    return (
        entry.session_id
        + ":"
        + entry.instrument_uid
    )
}


export function PhantomAuditCard({
    onResolved,
}: {
    onResolved?: () => void
}) {
    const [
        phantoms,
        setPhantoms,
    ] = useState<
        PhantomEntry[]
    >([])

    const [
        errors,
        setErrors,
    ] = useState<
        string[]
    >([])

    const [
        checkedAccounts,
        setCheckedAccounts,
    ] = useState<
        string[]
    >([])

    const [
        selected,
        setSelected,
    ] = useState<
        Record<
            string,
            boolean
        >
    >({})

    const [
        isChecking,
        setIsChecking,
    ] = useState(
        false
    )

    const [
        isResolving,
        setIsResolving,
    ] = useState(
        false
    )

    const [
        message,
        setMessage,
    ] = useState<
        string | null
    >(null)

    const [
        error,
        setError,
    ] = useState<
        string | null
    >(null)

    const [
        hasResult,
        setHasResult,
    ] = useState(
        false
    )


    function checkPhantoms() {
        setIsChecking(
            true
        )

        setMessage(
            null
        )

        setError(
            null
        )

        getPhantoms()
            .then(
                data => {
                    setPhantoms(
                        data.phantoms
                    )

                    setErrors(
                        data.errors
                    )

                    setCheckedAccounts(
                        data.checked_accounts
                    )

                    setSelected(
                        {}
                    )

                    setHasResult(
                        true
                    )
                }
            )
            .catch(
                err => {
                    setError(
                        err instanceof Error
                            ? err.message
                            : String(
                                err
                            )
                    )
                }
            )
            .finally(
                () => {
                    setIsChecking(
                        false
                    )
                }
            )
    }


    function toggleEntry(
        entry: PhantomEntry
    ) {
        const key = (
            entryKey(
                entry
            )
        )

        setSelected(
            current => ({
                ...current,

                [key]:
                    !current[
                        key
                    ],
            })
        )
    }


    function resolveSelected() {
        const bySession = new Map<
            string,
            Set<
                string
            >
        >()

        for (
            const entry
            of phantoms
        ) {
            if (
                !selected[
                    entryKey(
                        entry
                    )
                ]
            ) {
                continue
            }

            const uids = (
                bySession.get(
                    entry.session_id
                )
                ?? new Set<
                    string
                >()
            )

            uids.add(
                entry.instrument_uid
            )

            bySession.set(
                entry.session_id,
                uids
            )
        }

        if (
            bySession.size
            === 0
        ) {
            return
        }

        const items = [
            ...bySession
        ].map(
            ([
                session_id,
                uids,
            ]) => ({
                session_id,

                instrument_uids: [
                    ...uids
                ],
            })
        )

        setIsResolving(
            true
        )

        setMessage(
            null
        )

        setError(
            null
        )

        resolvePhantoms(
            items
        )
            .then(
                data => {
                    const removed = (
                        data
                        .resolved
                        .reduce(
                            (
                                total,
                                item,
                            ) => (
                                total
                                + item.removed_instruments
                            ),

                            0
                        )
                    )

                    setMessage(
                        "Удалено из истории: "
                        + removed
                        + " инструмент(ов)."
                    )

                    onResolved?.()

                    return (
                        getPhantoms()
                    )
                }
            )
            .then(
                data => {
                    setPhantoms(
                        data.phantoms
                    )

                    setErrors(
                        data.errors
                    )

                    setCheckedAccounts(
                        data.checked_accounts
                    )

                    setSelected(
                        {}
                    )
                }
            )
            .catch(
                err => {
                    setError(
                        err instanceof Error
                            ? err.message
                            : String(
                                err
                            )
                    )
                }
            )
            .finally(
                () => {
                    setIsResolving(
                        false
                    )
                }
            )
    }


    const selectedCount = (
        Object
        .values(
            selected
        )
        .filter(
            Boolean
        )
        .length
    )


    return (
        <div
            style={{
                background:
                "white",

                borderRadius:
                14,

                padding:
                13,

                marginTop:
                10,
            }}
        >
            <h3
                style={{
                    marginTop:
                    0,

                    marginBottom:
                    10,
                }}
            >
                Сверка фантомов
            </h3>

            <div
                style={{
                    color:
                    "#6b7280",

                    fontSize:
                    13,

                    marginBottom:
                    10,
                }}
            >
                Проверяет сохранённые позиции и ордера по всем счётам.
                Если в истории есть позиции/ордера, а на счёте брокера
                по инструменту пусто — их можно удалить из истории
                (только с вашего подтверждения).
            </div>

            <button
                onClick={
                    checkPhantoms
                }

                disabled={
                    isChecking
                }

                style={{
                    padding:
                    "8px 14px",

                    borderRadius:
                    8,

                    border:
                    "1px solid #d1d5db",

                    background:
                    isChecking
                        ? "#e5e7eb"
                        : "white",

                    cursor:
                    isChecking
                        ? "default"
                        : "pointer",
                }}
            >
                {
                    isChecking
                        ? "Проверка..."
                        : "Проверить фантомы"
                }
            </button>

            {hasResult && (
                <div
                    style={{
                        marginTop:
                        10,

                        fontSize:
                        13,

                        color:
                        "#6b7280",
                    }}
                >
                    Проверено счетов: {
                        checkedAccounts.length
                    }
                </div>
            )}

            {errors.length > 0 && (
                <div
                    style={{
                        marginTop:
                        10,

                        padding:
                        "8px 10px",

                        borderRadius:
                        8,

                        background:
                        "#fef2f2",

                        color:
                        "#b91c1c",

                        fontSize:
                        12,
                    }}
                >
                    {
                        errors.map(
                            item => (
                                <div
                                    key={
                                        item
                                    }
                                >
                                    {
                                        item
                                    }
                                </div>
                            )
                        )
                    }
                </div>
            )}

            {phantoms.length > 0 && (
                <>
                    <div
                        style={{
                            marginTop:
                            12,

                            marginBottom:
                            6,

                            fontWeight:
                            700,

                            fontSize:
                            13,

                            color:
                            "#b91c1c",
                        }}
                    >
                        Найдены фантомы:
                        {" "}
                        {
                            phantoms.length
                        }
                    </div>

                    {phantoms.map(
                        entry => {
                            const key = (
                                entryKey(
                                    entry
                                )
                            )

                            return (
                                <label
                                    key={
                                        key
                                    }

                                    style={{
                                        display:
                                        "flex",

                                        alignItems:
                                        "center",

                                        gap:
                                        10,

                                        padding:
                                        "8px 0",

                                        borderTop:
                                        "1px solid #e5e7eb",

                                        cursor:
                                        "pointer",

                                        fontSize:
                                        13,
                                    }}
                                >
                                    <input
                                        type=
                                            "checkbox"

                                        checked={
                                            (
                                                selected[
                                                    key
                                                ]
                                                === true
                                            )
                                        }

                                        onChange={() =>
                                            toggleEntry(
                                                entry
                                            )
                                        }
                                    />

                                    <div>
                                        <b>
                                            {
                                                entry.ticker
                                            }
                                        </b>

                                        {" — "}

                                        позиций: {
                                            entry.open_positions
                                        }

                                        {" ("}

                                        {
                                            entry.open_lots
                                        }

                                        {" лотов), ордеров: "}

                                        {
                                            entry.active_orders
                                        }

                                        {", у брокера: "}

                                        {
                                            entry.broker_lots
                                        }

                                        {" лотов · режим "}

                                        {
                                            entry.mode
                                        }

                                        {" · сессия "}

                                        <span
                                            style={{
                                                color:
                                                "#6b7280",

                                                wordBreak:
                                                "break-all",
                                            }}
                                        >
                                            {
                                                entry.session_id
                                            }
                                        </span>
                                    </div>
                                </label>
                            )
                        }
                    )}

                    <button
                        onClick={
                            resolveSelected
                        }

                        disabled={
                            isResolving
                            || selectedCount
                            === 0
                        }

                        style={{
                            marginTop:
                            10,

                            padding:
                            "8px 14px",

                            borderRadius:
                            8,

                            border:
                            "1px solid #b91c1c",

                            background:
                            (
                                isResolving
                                || selectedCount
                                === 0
                            )
                                ? "#e5e7eb"
                                : "#b91c1c",

                            color:
                            "white",

                            cursor:
                            (
                                isResolving
                                || selectedCount
                                === 0
                            )
                                ? "default"
                                : "pointer",
                        }}
                    >
                        {
                            isResolving
                                ? "Удаление..."
                                : "Удалить выбранные из истории"
                                + (
                                    selectedCount
                                    > 0
                                        ? ` (${selectedCount})`
                                        : ""
                                )
                        }
                    </button>
                </>
            )}

            {hasResult
                && phantoms.length
                === 0 && (
                    <div
                        style={{
                            marginTop:
                            10,

                            fontSize:
                            13,

                            color:
                            "#15803d",
                        }}
                    >
                        Фантомов не найдено — история совпадает со счетами.
                    </div>
                )}

            {message && (
                <div
                    style={{
                        marginTop:
                        10,

                        fontSize:
                        13,

                        color:
                        "#15803d",
                    }}
                >
                    {
                        message
                    }
                </div>
            )}

            {error && (
                <div
                    style={{
                        marginTop:
                        10,

                        fontSize:
                        13,

                        color:
                        "#b91c1c",
                    }}
                >
                    {
                        error
                    }
                </div>
            )}
        </div>
    )
}
