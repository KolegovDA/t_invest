import type { Instrument } from "../types"


type Props = {
    instrument: Instrument
    onConfigure: (instrument: Instrument) => void
    onRemove: (ticker: string) => void
}


export function InstrumentCard({
    instrument,
    onConfigure,
    onRemove,
}: Props) {
    return (
        <div
            style={{
                background: "white",
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

                    <div
                        style={{
                            color: "#6b7280",
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
                        ? `${instrument.price.toLocaleString()} ₽`
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
                    <div style={{ color: "#9ca3af" }}>
                        Базовый лот
                    </div>

                    <b>
                        {instrument.quantity ?? 1}
                    </b>
                </div>

                <div>
                    <div style={{ color: "#9ca3af" }}>
                        Капитал
                    </div>

                    <b>
                        {instrument.required_capital.toLocaleString()} ₽
                    </b>
                </div>
            </div>

            <div
                style={{
                    display: "flex",
                    gap: 8,
                    marginTop: 16,
                }}
            >
                <button
                    onClick={() =>
                        onConfigure(instrument)
                    }
                    style={{
                        flex: 1,
                        padding: 12,
                        borderRadius: 11,
                        border:
                            "1px solid #d1d5db",
                        background: "white",
                        fontWeight: 600,
                    }}
                >
                    Настроить
                </button>

                <button
                    onClick={() =>
                        onRemove(instrument.ticker)
                    }
                    style={{
                        padding: "12px 16px",
                        borderRadius: 11,
                        border:
                            "1px solid #fecaca",
                        background: "#fff",
                        color: "#dc2626",
                    }}
                >
                    Удалить
                </button>
            </div>
        </div>
    )
}
