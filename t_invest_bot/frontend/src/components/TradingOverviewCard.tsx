import { useState } from "react"

import type {
    AccountsOverview,
    ActiveSession,
    OverviewAccount,
    OverviewSessionBlock,
} from "../types"

function formatMoney(value: number | null | undefined): string {
    return value == null ? "—" : value.toLocaleString("ru-RU", { maximumFractionDigits: 2 })
}

function Metric({ label, value }: { label: string; value: string }) {
    return (
        <div style={{ minWidth: 80, flex: 1 }}>
            <div style={{ fontSize: 11, color: "var(--text-muted)" }}>{label}</div>
            <b>{value}</b>
        </div>
    )
}

function SessionBlock({ session, active, onOpen }: {
    session: OverviewSessionBlock
    active?: ActiveSession
    onOpen: () => void
}) {
    const profit = session.total_profit ?? 0
    return (
        <div style={{ background: "var(--card)", borderRadius: 16, padding: 16, marginBottom: 10 }}>
            <button onClick={onOpen} style={{ display: "flex", alignItems: "center", gap: 12, width: "100%", border: "none", background: "transparent", padding: 0, textAlign: "left", color: "var(--text)", cursor: "pointer" }}>
                <span style={{ width: 36, height: 36, borderRadius: "50%", display: "grid", placeItems: "center", background: "var(--card-soft)", color: "var(--accent)", fontWeight: 700 }}>{session.ticker.charAt(0)}</span>
                <span style={{ flex: 1 }}>
                    <b>{session.ticker}</b>
                    <span style={{ display: "block", marginTop: 3, color: "var(--text-muted)", fontSize: 12 }}>
                        {session.status} · Уровней: {active?.levels ?? session.orders_bought.length + session.orders_planned.length} · Лот: {active?.quantity ?? session.quantity} · Позиций: {session.positions}
                    </span>
                </span>
                <span style={{ color: profit < 0 ? "var(--loss)" : "var(--profit)", fontWeight: 700 }}>{formatMoney(profit)}</span>
                <span style={{ color: "var(--text-dim)" }}>›</span>
            </button>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "10px 14px", marginTop: 10 }}>
                <Metric label="Цена" value={formatMoney(session.current_price)} />
                <Metric label="Кол-во" value={formatMoney(session.quantity)} />
                <Metric label="Закрыто" value={String(session.closed_orders ?? 0)} />
                <Metric label="Прибыль сетки" value={formatMoney(session.cycle_profit)} />
                <Metric label="PnL" value={session.pnl_percent == null ? "—" : `${formatMoney(session.pnl_percent)}%`} />
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 12, marginTop: 12, paddingTop: 10, borderTop: "1px solid var(--border)" }}>
                <Metric label="Запуск тралла покупки" value={formatMoney(session.next_buy_activation)} />
                <Metric label="Запуск тралла продажи" value={formatMoney(session.next_sell_activation)} />
            </div>
        </div>
    )
}

export function TradingAccountDetails({ account, sessions, onOpenTicker }: {
    account: OverviewAccount
    sessions: ActiveSession[]
    onOpenTicker: (ticker: string) => void
}) {
    return (
        <div style={{ marginTop: 14 }}>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 14, padding: "10px 12px", marginBottom: 10, background: "var(--card-soft)", borderRadius: 12 }}>
                <Metric label="Зарезервировано" value={`${formatMoney(account.reserved)} ${account.currency}`} />
                <Metric label="Свободно" value={`${formatMoney(account.available)} ${account.currency}`} />
                <Metric label="В активе" value={`${formatMoney(account.invested)} ${account.currency}`} />
            </div>
            {account.sessions.map(session => {
                const active = sessions.find(item => item.ticker === session.ticker && (item.trading_account_id ?? account.id) === account.id)
                    ?? sessions.find(item => item.ticker === session.ticker)
                return <SessionBlock key={session.ticker} session={session} active={active} onOpen={() => onOpenTicker(session.ticker)} />
            })}
            {account.sessions.length === 0 && (
                <div style={{ fontSize: 13, color: "var(--text-muted)" }}>Нет активных сеток.</div>
            )}
        </div>
    )
}

function TradingAccountBlock({ account, sessions, onOpenTicker }: {
    account: OverviewAccount
    sessions: ActiveSession[]
    onOpenTicker: (ticker: string) => void
}) {
    const [expanded, setExpanded] = useState(account.sessions.length > 0)
    return (
        <div style={{ background: "var(--card)", borderRadius: 16, padding: "14px 16px", marginBottom: 12 }}>
            <button
                onClick={() => setExpanded(current => !current)}
                aria-expanded={expanded}
                style={{ width: "100%", display: "flex", alignItems: "center", gap: 12, padding: 0, border: "none", background: "transparent", textAlign: "left", color: "var(--text)", cursor: "pointer" }}
            >
                <div style={{ flex: 1 }}>
                    <b>{account.name}</b>
                    <div style={{ marginTop: 4, fontSize: 12, color: "var(--text-muted)" }}>
                        {account.broker} · {account.currency} · {account.sessions.length} сессий
                    </div>
                </div>
                <span>{expanded ? "▴" : "▾"}</span>
            </button>
            {expanded && <TradingAccountDetails account={account} sessions={sessions} onOpenTicker={onOpenTicker} />}
        </div>
    )
}

export function TradingOverviewCard({ overview, sessions = [], onOpenTicker }: {
    overview: AccountsOverview | null
    sessions?: ActiveSession[]
    onOpenTicker: (ticker: string) => void
}) {
    if (overview === null) {
        return <div style={{ color: "var(--text-muted)", fontSize: 13 }}>Загрузка...</div>
    }
    if (overview.accounts.length === 0) {
        return <div style={{ color: "var(--text-muted)", fontSize: 13 }}>Счета пока не добавлены.</div>
    }
    return (
        <div>
            {overview.accounts.map(account => (
                <TradingAccountBlock key={account.id} account={account} sessions={sessions} onOpenTicker={onOpenTicker} />
            ))}
        </div>
    )
}
