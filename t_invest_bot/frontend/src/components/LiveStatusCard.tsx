import type { LiveStatus } from "../types"

type Props = {
    status: LiveStatus | null
}

export function LiveStatusCard({
    status,
}: Props) {
    if (!status) {
        return null
    }

    return (
        <div style={cardStyle}>
            <h2 style={{ marginTop: 0 }}>
                Боевой счёт
            </h2>

            <StatusRow
                label="Production token"
                value={
                    status.token_configured
                        ? "OK"
                        : "Нет"
                }
            />

            <StatusRow
                label="Режим"
                value={status.trading_mode}
            />

            <StatusRow
                label="Live execution"
                value={
                    status.live_trading_enabled
                        ? "ВКЛЮЧЕН"
                        : "ОТКЛЮЧЕН"
                }
            />

            <StatusRow
                label="Счёт выбран"
                value={
                    status.account_found
                        ? "Да"
                        : "Нет"
                }
            />

            {status.error && (
                <div style={errorStyle}>
                    {status.error}
                </div>
            )}

            <h3>Доступные счета</h3>

            {status.accounts.map(account => (
                <div
                    key={account.account_id}
                    style={accountStyle}
                >
                    <b>
                        {account.name || "T-Invest"}
                    </b>

                    <div>
                        {account.account_id}
                    </div>

                    {account.selected && (
                        <div style={selectedStyle}>
                            Выбран
                        </div>
                    )}
                </div>
            ))}

            {status.portfolio && (
                <>
                    <h3>Портфель</h3>

                    <StatusRow
                        label="Акции"
                        value={`${Number(
                            status.portfolio
                                .total_amount_shares
                        ).toLocaleString()} ₽`}
                    />

                    <StatusRow
                        label="Облигации"
                        value={`${Number(
                            status.portfolio
                                .total_amount_bonds
                        ).toLocaleString()} ₽`}
                    />

                    <StatusRow
                        label="ETF"
                        value={`${Number(
                            status.portfolio
                                .total_amount_etf
                        ).toLocaleString()} ₽`}
                    />

                    <StatusRow
                        label="Валюта"
                        value={`${Number(
                            status.portfolio
                                .total_amount_currencies
                        ).toLocaleString()} ₽`}
                    />

                    <StatusRow
                        label="Позиций"
                        value={String(
                            status.portfolio
                                .positions_count
                        )}
                    />

                    <StatusRow
                        label="Доходность"
                        value={`${status.portfolio.expected_yield}%`}
                    />
                </>
            )}

            <h3>API</h3>

            <StatusRow
                label="Unary limit groups"
                value={String(
                    status.unary_limits_count
                )}
            />

            <StatusRow
                label="Stream limit groups"
                value={String(
                    status.stream_limits_count
                )}
            />
        </div>
    )
}

function StatusRow({
    label,
    value,
}: {
    label: string
    value: string
}) {
    return (
        <div style={rowStyle}>
            <span>{label}</span>
            <b>{value}</b>
        </div>
    )
}

const cardStyle = {
    background: "white",
    borderRadius: 18,
    padding: 16,
    marginBottom: 16,
}

const rowStyle = {
    display: "flex",
    justifyContent: "space-between",
    gap: 12,
    padding: "11px 0",
    borderBottom: "1px solid #f3f4f6",
}

const accountStyle = {
    padding: 12,
    background: "#f9fafb",
    borderRadius: 12,
    marginBottom: 8,
    wordBreak: "break-all" as const,
}

const selectedStyle = {
    marginTop: 6,
    color: "#16a34a",
    fontWeight: 700,
}

const errorStyle = {
    padding: 12,
    marginTop: 12,
    borderRadius: 12,
    background: "#fee2e2",
    color: "#991b1b",
    wordBreak: "break-word" as const,
}
