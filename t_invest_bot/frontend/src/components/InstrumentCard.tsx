import type { Instrument } from "../types"


type Props = {
    instrument: Instrument
    onConfigure: (instrument: Instrument) => void
    onRemove: (ticker: string) => void
    disabled?: boolean
    name?: string
    volatilityPercent?: string
    riskBand?: string
}


export function InstrumentCard({
    instrument,
    onConfigure,
    onRemove,
    disabled = false,
    name,
    volatilityPercent,
    riskBand,
}: Props) {
    return (
        <div
            style={{
                background: "var(--card)",
                borderRadius: 18,
                padding: 16,
                marginBottom: 12,
                boxShadow:
                    "0 4px 14px rgba(0,0,0,0.05)",
            }}
        >
            <div
                style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "flex-start",
                }}
            >
                <div>
                    <h3
                        style={{
                            margin: 0,
                            fontSize: 21,
                        }}
                    >
                        {instrument.ticker}
                    </h3>
                    {name && <div style={{ color: "var(--text-muted)", fontSize: 13 }}>{name}</div>}

                    <div
                        style={{
                            color: "var(--text-muted)",
                            marginTop: 5,
                        }}
                    >
                        {instrument.levels} уровней
                    </div>
                </div>

                <div
                    style={{
                        fontWeight: 700,
                        fontSize: 18,
                    }}
                >
                    {instrument.price > 0
                        ? `${instrument.price.toLocaleString("ru-RU", { maximumFractionDigits: 2 })} ₽`
                        : "—"}
                </div>
            </div>

            <div
                style={{
                    marginTop: 16,
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr",
                    gap: 8,
                    fontSize: 14,
                }}
            >
                <div>
                    <div style={{ color: "var(--text-dim)" }}>
                        Базовый лот
                    </div>

                    <b>
                        {instrument.quantity ?? 1}
                    </b>
                </div>

                <div>
                    <div style={{ color: "var(--text-dim)" }}>
                        Капитал
                    </div>

                    <b>
                        {(instrument.required_capital ?? 0).toLocaleString("ru-RU", { maximumFractionDigits: 2 })} ₽
                    </b>
                </div>
            </div>

            {(volatilityPercent !== undefined || riskBand) && <div style={{ marginTop: 8, fontSize: 12, color: "var(--text-muted)" }}>
                {volatilityPercent !== undefined && <>Волатильность: {Number(volatilityPercent).toLocaleString("ru-RU", { maximumFractionDigits: 2 })}%</>}
                {riskBand && <> · {riskBand}</>}
            </div>}

            <div
                style={{
                    display: "flex",
                    gap: 8,
                    marginTop: 16,
                }}
            >
                <button
                    type="button"
                    disabled={disabled}
                    onClick={() =>
                        onConfigure(instrument)
                    }
                    style={{
                        flex: 1,
                        padding: 12,
                        borderRadius: 11,
                        border:
                            "1px solid var(--border)",
                        background: "var(--card)",
                        fontWeight: 600,
                    }}
                >
                    Настроить
                </button>

                <button
                    type="button"
                    disabled={disabled}
                    onClick={() =>
                        onRemove(instrument.ticker)
                    }
                    style={{
                        padding: "12px 16px",
                        borderRadius: 11,
                        border:
                            "1px solid #fecaca",
                        background: "var(--card)",
                        color: "var(--loss)",
                    }}
                >
                    Удалить
                </button>
            </div>
        </div>
    )
}
