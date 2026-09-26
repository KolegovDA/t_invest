import {
    useEffect,
    useState,
} from "react"

import type {
    CSSProperties,
} from "react"

import {
    getSelectionOptions,
    previewAutoSelection,
    previewIndexSelection,
    previewInstrumentSelection,
} from "../api"

import type {
    GridSelectionPlan,
    InstrumentSelectionPreview,
    SelectionOptions,
} from "../types"


type TabMode =
    | "index"
    | "manual"
    | "auto"


type CandidateForm = {
    ticker:
    string

    risk_value:
    string

    confidence_value:
    string
}


const inputStyle: CSSProperties =
    {
        flex: 1,

        minWidth: 60,

        padding: 10,

        borderRadius: 10,

        border:
        "1px solid #e5e7eb",

        fontSize: 14,
    }


const tabStyle = (
    active: boolean,
): CSSProperties =>
    ({
        flex: 1,

        padding: 10,

        borderRadius: 10,

        border:
        active
        ? "1px solid #2563eb"
        : "1px solid #e5e7eb",

        background:
        active
        ? "#eff6ff"
        : "transparent",

        color:
        active
        ? "#2563eb"
        : "#6b7280",

        fontWeight: 700,

        cursor: "pointer",
    })


const actionButtonStyle = (
    busy: boolean,
): CSSProperties =>
    ({
        width: "100%",

        padding: 12,

        borderRadius: 10,

        border: "none",

        background:
        busy
        ? "#93c5fd"
        : "#2563eb",

        color: "white",

        fontWeight: 700,

        cursor:
        busy
        ? "default"
        : "pointer",
    })


export function InstrumentSelectionCard() {
    const [
        tab,
        setTab,
    ] = useState<
        TabMode
    >(
        "index"
    )

    const [
        capital,
        setCapital,
    ] = useState(
        "100000"
    )

    const [
        quantity,
        setQuantity,
    ] = useState(
        "1"
    )

    const [
        options,
        setOptions,
    ] = useState<
        SelectionOptions | null
    >(null)

    const [
        selectedIndexId,
        setSelectedIndexId,
    ] = useState(
        "blue_chips"
    )

    const [
        maxInstruments,
        setMaxInstruments,
    ] = useState(
        5
    )

    const [
        minConfidence,
        setMinConfidence,
    ] = useState(
        "40"
    )

    const [
        allowHighRisk,
        setAllowHighRisk,
    ] = useState(
        false
    )

    const [
        candidates,
        setCandidates,
    ] = useState<
        CandidateForm[]
    >([
        {
            ticker:
            "",

            risk_value:
            "20",

            confidence_value:
            "",
        },
    ])

    const [
        autoMaxInstruments,
        setAutoMaxInstruments,
    ] = useState(
        5
    )

    const [
        autoMaxPrice,
        setAutoMaxPrice,
    ] = useState(
        ""
    )

    const [
        plan,
        setPlan,
    ] = useState<
        GridSelectionPlan | null
    >(null)

    const [
        manualPreview,
        setManualPreview,
    ] = useState<
        InstrumentSelectionPreview | null
    >(null)

    const [
        error,
        setError,
    ] = useState<
        string | null
    >(null)

    const [
        isCalculating,
        setIsCalculating,
    ] = useState(
        false
    )

    useEffect(
        () => {
            let cancelled =
                false

            getSelectionOptions()
                .then(
                    result => {
                        if (
                            !cancelled
                        ) {
                            setOptions(
                                result
                            )
                        }
                    }
                )

                .catch(
                    () => {
                        //
                    }
                )

            return () => {
                cancelled =
                    true
            }
        },

        []
    )

    const selectedPreset =
        options?.indexes.find(
            index =>
                index.index_id
                === selectedIndexId
        )

    function updateCandidate(
        index: number,

        patch: Partial<CandidateForm>
    ) {
        setCandidates(
            current =>
                current.map(
                    (
                        candidate,
                        candidateIndex
                    ) =>
                        candidateIndex
                        === index

                        ? {
                            ...candidate,
                            ...patch,
                        }

                        : candidate
                )
        )
    }

    function addCandidate() {
        setCandidates(
            current => [
                ...current,

                {
                    ticker:
                    "",

                    risk_value:
                    "20",

                    confidence_value:
                    "",
                },
            ]
        )
    }

    function removeCandidate(
        index: number
    ) {
        setCandidates(
            current =>
                current.filter(
                    (
                        _candidate,
                        candidateIndex
                    ) =>
                        candidateIndex
                        !== index
                )
        )
    }

    function readCapital():
        string | null {
        const capitalValue =
            capital.trim()

        if (
            !capitalValue
            || Number(
                capitalValue
            )
            <= 0
        ) {
            setError(
                "Укажите капитал больше нуля."
            )

            return null
        }

        return capitalValue
    }

    function readQuantity():
        number | null {
        const quantityValue =
            Math.max(
                1,

                Math.trunc(
                    Number(
                        quantity.trim()
                        || "1"
                    )
                )
            )

        if (
            !Number.isFinite(
                quantityValue
            )
        ) {
            setError(
                "Количество штук должно быть числом."
            )

            return null
        }

        return quantityValue
    }

    async function calculateIndex() {
        const capitalValue =
            readCapital()

        if (
            capitalValue
            === null
        ) {
            return
        }

        const quantityValue =
            readQuantity()

        if (
            quantityValue
            === null
        ) {
            return
        }

        setIsCalculating(
            true
        )

        setError(
            null
        )

        setPlan(
            null
        )

        try {
            const result =
                await previewIndexSelection(
                    {
                        index_id:
                        selectedIndexId,

                        capital:
                        capitalValue,

                        quantity:
                        quantityValue,
                    }
                )

            setPlan(
                result
            )

        } catch (calculateError) {
            setError(
                calculateError instanceof Error
                ? calculateError.message
                : String(
                    calculateError
                )
            )

        } finally {
            setIsCalculating(
                false
            )
        }
    }

    async function calculateAuto() {
        const capitalValue =
            readCapital()

        if (
            capitalValue
            === null
        ) {
            return
        }

        const quantityValue =
            readQuantity()

        if (
            quantityValue
            === null
        ) {
            return
        }

        const maxPriceValue =
            autoMaxPrice.trim()

        setIsCalculating(
            true
        )

        setError(
            null
        )

        setPlan(
            null
        )

        try {
            const result =
                await previewAutoSelection(
                    {
                        capital:
                        capitalValue,

                        quantity:
                        quantityValue,

                        max_instruments:
                        autoMaxInstruments,

                        max_price:
                        maxPriceValue
                        || null,
                    }
                )

            setPlan(
                result
            )

        } catch (calculateError) {
            setError(
                calculateError instanceof Error
                ? calculateError.message
                : String(
                    calculateError
                )
            )

        } finally {
            setIsCalculating(
                false
            )
        }
    }

    async function calculateManual() {
        const capitalValue =
            readCapital()

        if (
            capitalValue
            === null
        ) {
            return
        }

        const filled =
            candidates.filter(
                candidate =>
                    candidate
                    .ticker
                    .trim()
            )

        if (
            filled.length
            === 0
        ) {
            setError(
                "Добавьте хотя бы один инструмент."
            )

            return
        }

        setIsCalculating(
            true
        )

        setError(
            null
        )

        setManualPreview(
            null
        )

        try {
            const result =
                await previewInstrumentSelection(
                    {
                        capital:
                        capitalValue,

                        max_instruments:
                        maxInstruments,

                        min_confidence:
                        minConfidence.trim()
                        || "40",

                        allow_high_risk:
                        allowHighRisk,

                        candidates:
                        filled.map(
                            candidate => ({
                                ticker:
                                candidate.ticker
                                .trim()
                                .toUpperCase(),

                                risk_value:
                                candidate.risk_value.trim()
                                || "0",

                                confidence_value:
                                candidate.confidence_value.trim(),
                            })
                        ),
                    }
                )

            setManualPreview(
                result
            )

        } catch (calculateError) {
            setError(
                calculateError instanceof Error
                ? calculateError.message
                : String(
                    calculateError
                )
            )

        } finally {
            setIsCalculating(
                false
            )
        }
    }

    return (
        <div
            style={{
                background:
                "white",
                borderRadius: 16,
                padding: 16,
                marginBottom: 16,
                boxShadow:
                "0 6px 16px rgba(0,0,0,0.06)",
            }}
        >
            <h2
                style={{
                    marginTop: 0,
                }}
            >
                Подбор инструментов
            </h2>

            <p
                style={{
                    color: "#6b7280",
                    fontSize: 13,
                }}
            >
                Три режима (v1.1): индексный — готовые составы, ручной — RiskScore/ConfidenceScore, авторежим — самые волатильные акции под капитал.
            </p>

            <div
                style={{
                    display: "flex",
                    gap: 8,
                    marginBottom: 12,
                }}
            >
                <button
                    style={
                        tabStyle(
                            tab
                            === "index"
                        )
                    }

                    onClick={() =>
                        setTab(
                            "index"
                        )
                    }
                >
                    Индекс
                </button>

                <button
                    style={
                        tabStyle(
                            tab
                            === "manual"
                        )
                    }

                    onClick={() =>
                        setTab(
                            "manual"
                        )
                    }
                >
                    Ручной
                </button>

                <button
                    style={
                        tabStyle(
                            tab
                            === "auto"
                        )
                    }

                    onClick={() =>
                        setTab(
                            "auto"
                        )
                    }
                >
                    Авто
                </button>
            </div>

            <div
                style={{
                    display: "flex",
                    gap: 8,
                    marginBottom: 12,
                }}
            >
                <input
                    style={
                        inputStyle
                    }
                    value={
                        capital
                    }
                    onChange={
                        event =>
                            setCapital(
                                event
                                    .target
                                    .value
                            )
                    }
                    placeholder="Капитал"
                    inputMode="decimal"
                />

                {tab !== "manual" && (
                    <input
                        style={
                            inputStyle
                        }
                        value={
                            quantity
                        }
                        onChange={
                            event =>
                                setQuantity(
                                    event
                                        .target
                                        .value
                                )
                        }
                        placeholder="Штук в уровень"
                        inputMode="numeric"
                    />
                )}
            </div>

            {tab === "index" && (
                <>
                    <select
                        style={{
                            ...inputStyle,
                            marginBottom: 8,
                        }}
                        value={
                            selectedIndexId
                        }
                        onChange={
                            event =>
                                setSelectedIndexId(
                                    event
                                        .target
                                        .value
                                )
                        }
                    >
                        {(
                            options?.indexes
                            ?? []
                        ).map(
                            index => (
                                <option
                                    key={
                                        index.index_id
                                    }

                                    value={
                                        index.index_id
                                    }
                                >
                                    {
                                        index.name
                                    }

                                    {" · "}

                                    {
                                        index.tickers_count
                                    }

                                    {" шт."}
                                </option>
                            )
                        )}
                    </select>

                    {selectedPreset && (
                        <p
                            style={{
                                color: "#6b7280",
                                fontSize: 13,
                                marginTop: 0,
                            }}
                        >
                            {
                                selectedPreset.description
                            }

                            {" Капитал делится равными долями, в каждую долю вписывается сетка до 30 уровней."}
                        </p>
                    )}

                    <button
                        onClick={
                            calculateIndex
                        }
                        disabled={
                            isCalculating
                        }
                        style={
                            actionButtonStyle(
                                isCalculating
                            )
                        }
                    >
                        {
                            isCalculating
                            ? "Расчёт..."
                            : "Рассчитать индекс"
                        }
                    </button>
                </>
            )}

            {tab === "manual" && (
                <>
                    <div
                        style={{
                            display: "flex",
                            gap: 8,
                            marginBottom: 12,
                        }}
                    >
                        <input
                            style={
                                inputStyle
                            }
                            value={
                                maxInstruments
                            }
                            onChange={
                                event =>
                                    setMaxInstruments(
                                        Math.max(
                                            1,

                                            Number(
                                                event
                                                    .target
                                                    .value
                                                || 1
                                            )
                                        )
                                    )
                            }
                            placeholder="Макс. инструментов"
                            inputMode="numeric"
                        />

                        <input
                            style={
                                inputStyle
                            }
                            value={
                                minConfidence
                            }
                            onChange={
                                event =>
                                    setMinConfidence(
                                        event
                                            .target
                                            .value
                                    )
                            }
                            placeholder="Min confidence"
                            inputMode="decimal"
                        />
                    </div>

                    <label
                        style={{
                            display: "flex",
                            alignItems: "center",
                            gap: 8,
                            fontSize: 13,
                            color: "#374151",
                            marginBottom: 12,
                        }}
                    >
                        <input
                            type="checkbox"
                            checked={
                                allowHighRisk
                            }
                            onChange={
                                event =>
                                    setAllowHighRisk(
                                        event
                                            .target
                                            .checked
                                    )
                            }
                        />

                        Разрешить высокий риск
                    </label>

                    {candidates.map(
                        (
                            candidate,
                            index
                        ) => (
                            <div
                                key={
                                    index
                                }
                                style={{
                                    display: "flex",
                                    gap: 8,
                                    marginBottom: 8,
                                }}
                            >
                                <input
                                    style={
                                        inputStyle
                                    }
                                    value={
                                        candidate.ticker
                                    }
                                    onChange={
                                        event =>
                                            updateCandidate(
                                                index,

                                                {
                                                    ticker:
                                                    event
                                                        .target
                                                        .value,
                                                }
                                            )
                                    }
                                    placeholder="Тикер"
                                />

                                <input
                                    style={
                                        inputStyle
                                    }
                                    value={
                                        candidate.risk_value
                                    }
                                    onChange={
                                        event =>
                                            updateCandidate(
                                                index,

                                                {
                                                    risk_value:
                                                    event
                                                        .target
                                                        .value,
                                                }
                                            )
                                    }
                                    placeholder="Risk 0-100"
                                    inputMode="decimal"
                                />

                                <input
                                    style={
                                        inputStyle
                                    }
                                    value={
                                        candidate.confidence_value
                                    }
                                    onChange={
                                        event =>
                                            updateCandidate(
                                                index,

                                                {
                                                    confidence_value:
                                                    event
                                                        .target
                                                        .value,
                                                }
                                            )
                                    }
                                    placeholder="Confidence"
                                    inputMode="decimal"
                                />

                                <button
                                    onClick={() =>
                                        removeCandidate(
                                            index
                                        )
                                    }
                                    style={{
                                        border: "none",
                                        background: "#fee2e2",
                                        color: "#b91c1c",
                                        borderRadius: 10,
                                        padding: "0 12px",
                                        cursor: "pointer",
                                        fontWeight: 700,
                                    }}
                                >
                                    ×
                                </button>
                            </div>
                        )
                    )}

                    <button
                        onClick={
                            addCandidate
                        }
                        style={{
                            width: "100%",
                            padding: 10,
                            borderRadius: 10,
                            border: "1px dashed #d1d5db",
                            background: "transparent",
                            color: "#6b7280",
                            cursor: "pointer",
                            marginBottom: 12,
                        }}
                    >
                        + Инструмент
                    </button>

                    <button
                        onClick={
                            calculateManual
                        }
                        disabled={
                            isCalculating
                        }
                        style={
                            actionButtonStyle(
                                isCalculating
                            )
                        }
                    >
                        {
                            isCalculating
                            ? "Расчёт..."
                            : "Рассчитать портфель"
                        }
                    </button>
                </>
            )}

            {tab === "auto" && (
                <>
                    <div
                        style={{
                            display: "flex",
                            gap: 8,
                            marginBottom: 8,
                        }}
                    >
                        <input
                            style={
                                inputStyle
                            }
                            value={
                                autoMaxInstruments
                            }
                            onChange={
                                event =>
                                    setAutoMaxInstruments(
                                        Math.max(
                                            1,

                                            Number(
                                                event
                                                    .target
                                                    .value
                                                || 1
                                            )
                                        )
                                    )
                            }
                            placeholder="Макс. инструментов"
                            inputMode="numeric"
                        />

                        <input
                            style={
                                inputStyle
                            }
                            value={
                                autoMaxPrice
                            }
                            onChange={
                                event =>
                                    setAutoMaxPrice(
                                        event
                                            .target
                                            .value
                                    )
                            }
                            placeholder="Макс. цена (₽)"
                            inputMode="decimal"
                        />
                    </div>

                    <p
                        style={{
                            color: "#6b7280",
                            fontSize: 13,
                            marginTop: 0,
                            marginBottom: 12,
                        }}
                    >
                        Жадно набираются самые волатильные акции из {options?.auto.universe_tickers_count ?? "40+"} ликвидных: каждой — сетка до 30 уровней (минимум 10) в пределах капитала. После полного закрытия сетки бот заменяет акцию на более волатильную и добирает активы до лимита.
                    </p>

                    <button
                        onClick={
                            calculateAuto
                        }
                        disabled={
                            isCalculating
                        }
                        style={
                            actionButtonStyle(
                                isCalculating
                            )
                        }
                    >
                        {
                            isCalculating
                            ? "Расчёт..."
                            : "Рассчитать авторежим"
                        }
                    </button>
                </>
            )}

            {error && (
                <div
                    style={{
                        marginTop: 12,
                        padding: 12,
                        borderRadius: 10,
                        background: "#fee2e2",
                        color: "#b91c1c",
                        fontSize: 13,
                    }}
                >
                    {
                        error
                    }
                </div>
            )}

            {tab === "manual"
            && manualPreview && (
                <div
                    style={{
                        marginTop: 12,
                    }}
                >
                    {manualPreview.selections.map(
                        selection => (
                            <div
                                key={
                                    selection.ticker
                                }
                                style={{
                                    borderTop:
                                    "1px solid #eee",
                                    paddingTop: 10,
                                    marginTop: 10,
                                }}
                            >
                                <div
                                    style={{
                                        display: "flex",
                                        justifyContent: "space-between",
                                        fontWeight: 700,
                                    }}
                                >
                                    <span>
                                        {
                                            selection.ticker
                                        }
                                    </span>

                                    <span>
                                        {
                                            selection.weight_percent
                                        }
                                        %
                                    </span>
                                </div>

                                <div
                                    style={{
                                        display: "flex",
                                        justifyContent: "space-between",
                                        color: "#6b7280",
                                        fontSize: 13,
                                        marginTop: 4,
                                    }}
                                >
                                    <span>
                                        Капитал:{" "}
                                        {
                                            selection.allocated_capital
                                        }
                                    </span>

                                    <span>
                                        Risk:{" "}
                                        {
                                            selection.risk_band
                                            ?? "—"
                                        }

                                        {" · "}

                                        Confidence:{" "}
                                        {
                                            selection.confidence_value
                                            ?? "—"
                                        }
                                    </span>
                                </div>
                            </div>
                        )
                    )}

                    {manualPreview.rejected.length > 0 && (
                        <div
                            style={{
                                marginTop: 12,
                                fontSize: 13,
                                color: "#6b7280",
                            }}
                        >
                            <b>
                                Отклонено:
                            </b>

                            {manualPreview.rejected.map(
                                rejected => (
                                    <div
                                        key={
                                            rejected.ticker
                                        }
                                        style={{
                                            marginTop: 4,
                                        }}
                                    >
                                        {
                                            rejected.ticker
                                        }
                                        {" — "}
                                        {
                                            rejected.reason
                                        }
                                    </div>
                                )
                            )}
                        </div>
                    )}

                    {manualPreview.selections.length
                    === 0 && (
                        <p
                            style={{
                                color: "#b91c1c",
                            }}
                        >
                            Ни один инструмент не прошёл фильтры.
                        </p>
                    )}
                </div>
            )}

            {tab !== "manual"
            && plan && (
                <div
                    style={{
                        marginTop: 12,
                    }}
                >
                    <div
                        style={{
                            display: "flex",
                            justifyContent: "space-between",
                            fontSize: 13,
                            color: "#374151",
                            fontWeight: 700,
                        }}
                    >
                        <span>
                            Потрачено:{" "}
                            {
                                plan.spent_capital
                            }
                            {" ₽"}
                        </span>

                        <span>
                            Остаток:{" "}
                            {
                                plan.remaining_capital
                            }
                            {" ₽"}
                        </span>
                    </div>

                    {plan.selections.map(
                        selection => (
                            <div
                                key={
                                    selection.ticker
                                }
                                style={{
                                    borderTop:
                                    "1px solid #eee",
                                    paddingTop: 10,
                                    marginTop: 10,
                                }}
                            >
                                <div
                                    style={{
                                        display: "flex",
                                        justifyContent: "space-between",
                                        fontWeight: 700,
                                    }}
                                >
                                    <span>
                                        {
                                            selection.ticker
                                        }

                                        {" — "}

                                        {
                                            selection.name
                                        }
                                    </span>

                                    <span>
                                        {
                                            selection.estimated_cost
                                        }
                                        {" ₽"}
                                    </span>
                                </div>

                                <div
                                    style={{
                                        display: "flex",
                                        justifyContent: "space-between",
                                        color: "#6b7280",
                                        fontSize: 13,
                                        marginTop: 4,
                                    }}
                                >
                                    <span>
                                        Цена:{" "}
                                        {
                                            selection.price
                                        }
                                        {" ₽"}

                                        {" · "}

                                        Уровней:{" "}
                                        {
                                            selection.levels
                                        }

                                        {" · "}

                                        Шт:{" "}
                                        {
                                            selection.quantity
                                        }
                                    </span>

                                    <span>
                                        Волатильность:{" "}
                                        {
                                            selection.volatility_percent
                                        }
                                        %

                                        {" · "}

                                        {
                                            selection.risk_band
                                            ?? "—"
                                        }
                                    </span>
                                </div>
                            </div>
                        )
                    )}

                    {plan.rejected.length > 0 && (
                        <div
                            style={{
                                marginTop: 12,
                                fontSize: 13,
                                color: "#6b7280",
                            }}
                        >
                            <b>
                                Отклонено:
                            </b>

                            {plan.rejected.slice(
                                0,
                                10
                            ).map(
                                rejected => (
                                    <div
                                        key={
                                            rejected.ticker
                                        }
                                        style={{
                                            marginTop: 4,
                                        }}
                                    >
                                        {
                                            rejected.ticker
                                        }
                                        {" — "}
                                        {
                                            rejected.reason
                                        }
                                    </div>
                                )
                            )}

                            {plan.rejected.length
                            > 10 && (
                                <div
                                    style={{
                                        marginTop: 4,
                                    }}
                                >
                                    {"...и ещё "}

                                    {
                                        plan
                                        .rejected
                                        .length
                                        - 10
                                    }
                                </div>
                            )}
                        </div>
                    )}

                    {plan.selections.length
                    === 0 && (
                        <p
                            style={{
                                color: "#b91c1c",
                            }}
                        >
                            Ни один инструмент не подошёл под капитал.
                        </p>
                    )}
                </div>
            )}
        </div>
    )
}
