import { useState } from "react"
import { AppModal } from "./AppModal"

import type {
    OperationLogEntry,
} from "../types"


const eventTypeLabels: Record<
    string,
    string
> = {
    BUY:
    "Покупка",

    SELL:
    "Продажа",

    ORDER_PLACED:
    "Ордер",

    ACCOUNT_ADDED:
    "Счёт добавлен",

    ACCOUNT_UPDATED:
    "Счёт обновлён",

    ACCOUNT_REMOVED:
    "Счёт удалён",

    PLATFORM_CONNECTED:
    "Платформа подключена",

    PLATFORM_UPDATED:
    "Ключи платформы обновлены",

    PHANTOMS_REMOVED:
    "Фантомы удалены",

    DEPOSIT:
    "Пополнение",

    WITHDRAWAL:
    "Вывод",

    COMMISSION:
    "Списание комиссии ЛК",

    COMMISSION_CHARGED: "Списание комиссии ЛК",

    BROKER_OPERATION: "Операция платформы",

    BROKER_COMMISSION: "Комиссия брокера",

    DIVIDEND: "Дивиденды",

    COUPON: "Купон",

    TAX: "Налог",

    ORDER_RECONCILE:
    "Сверка ордеров",

    POSITION_CLEARED:
    "Позиции сняты",

    POSITION_MISMATCH:
    "Расхождение позиций",

    RECONCILE_ERROR:
    "Ошибка сверки",
}


const eventTypeColors: Record<
    string,
    string
> = {
    BUY: "var(--profit)",

    SELL: "var(--loss)",

    ORDER_PLACED: "var(--text-muted)",

    ACCOUNT_ADDED: "var(--accent)",

    ACCOUNT_UPDATED: "var(--accent)",

    ACCOUNT_REMOVED: "var(--accent)",

    PHANTOMS_REMOVED: "var(--accent)",

    DEPOSIT: "var(--profit)",

    WITHDRAWAL: "var(--loss)",

    COMMISSION: "var(--loss)",

    COMMISSION_CHARGED: "var(--loss)",

    ORDER_RECONCILE: "var(--text-muted)",

    POSITION_CLEARED: "var(--loss)",

    POSITION_MISMATCH: "var(--accent)",

    RECONCILE_ERROR: "var(--loss)",
}


function formatEventType(
    eventType: string
): string {
    return (
        eventTypeLabels[
            eventType
        ]
        ?? eventType
    )
}


function formatEventColor(
    eventType: string
): string {
    return (
        eventTypeColors[
            eventType
        ]
        ?? "var(--text)"
    )
}


function formatTime(
    createdAt: string
): string {
    const date =
        new Date(
            createdAt
        )

    if (
        Number.isNaN(
            date.getTime()
        )
    ) {
        return createdAt
    }

    return (
        date.toLocaleString(
            "ru-RU",
            {
                day: "2-digit",
                month: "2-digit",
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
            }
        )
    )
}


export function OperationsHistoryCard({
    operations,
}: {
    operations:
    OperationLogEntry[]
}) {
    const [gridHistory, setGridHistory] = useState<any[] | null>(null)
    const [gridError, setGridError] = useState<string | null>(null)
    async function loadGridHistory() {
        try {
            const response = await fetch('/api/grid-history')
            if (!response.ok) throw new Error(`HTTP ${response.status}`)
            const data = await response.json()
            setGridHistory(data.grids)
            setGridError(null)
        } catch (error) { setGridError(String(error)) }
    }
    return (
        <div
            style={{
                background: "var(--card)",

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
                История операций
            </h3>
            <button onClick={loadGridHistory} style={{ border: 'none', borderRadius: 8, padding: '8px 12px', background: 'var(--card-soft)', color: 'var(--accent)', cursor: 'pointer' }}>Закрытые сетки</button>
            {gridError && <div style={{ color: 'var(--loss)' }}>{gridError}</div>}
            {gridHistory !== null && <AppModal title="История закрытых сеток" onClose={() => setGridHistory(null)}>
                {gridHistory.length === 0 ? <div>Закрытых сеток пока нет.</div> : gridHistory.map(grid => {
                    const validPoint = (point: any) => Number.isFinite(point.price) && point.price > 0 && Number.isFinite(Date.parse(point.time))
                    const eventPoints = (grid.events || []).map((event: any) => ({ ...event, price: Number(/цена=([\d.]+)/.exec(event.details)?.[1]) })).filter(validPoint)
                    const pricePoints = (grid.price_points || []).map((point: any) => ({ ...point, price: Number(point.price) })).filter(validPoint).sort((left: any, right: any) => Date.parse(left.time) - Date.parse(right.time))
                    const tradePoints = eventPoints.filter((point: any) => point.side === "BUY" || point.side === "SELL")
                    const trailingPoints = eventPoints.filter((point: any) => point.side === "TRAILING")
                    const points = [...pricePoints, ...eventPoints].sort((left: any, right: any) => Date.parse(left.time) - Date.parse(right.time))
                    const basePrice = pricePoints[0]?.price ?? tradePoints[0]?.price ?? points[0]?.price ?? 1
                    const relativePrice = (price: number) => (price / basePrice - 1) * 100
                    const min = points.length ? Math.min(...points.map((point: any) => relativePrice(point.price))) : 0
                    const max = points.length ? Math.max(...points.map((point: any) => relativePrice(point.price))) : 0
                    const start = points.length ? Math.min(...points.map((point: any) => Date.parse(point.time))) : 0
                    const end = points.length ? Math.max(...points.map((point: any) => Date.parse(point.time))) : 0
                    const x = (time: string) => 10 + (Date.parse(time) - start) / Math.max(end - start, 1) * 620
                    const y = (price: number) => 280 - (relativePrice(price) - min) / Math.max(max - min, 0.01) * 260
                    return <details key={grid.grid_id} style={{ background: 'var(--card-soft)', padding: 12, borderRadius: 12, marginBottom: 12 }}>
                        <summary>{grid.ticker} · {formatTime(grid.closed_at)} · прибыль {grid.profit} · закрыто {grid.closed_orders}</summary>
                        {points.length > 0 && <svg viewBox="0 0 640 300" style={{ width: '100%', height: 300 }}>
                            <path d={pricePoints.map((point: any, index: number) => `${index ? 'L' : 'M'}${x(point.time)},${y(point.price)}`).join(' ')} fill="none" stroke="var(--accent)" />
                            {trailingPoints.map((point: any, index: number) => <circle key={`trail-${index}`} cx={x(point.time)} cy={y(point.price)} r="3" fill="#a78bfa"><title>Тралл · {point.price}</title></circle>)}
                            {tradePoints.map((point: any, index: number) => <circle key={`trade-${index}`} cx={x(point.time)} cy={y(point.price)} r="4" fill={point.side === 'BUY' ? 'var(--profit)' : 'var(--loss)'}><title>{point.side} · {point.price}</title></circle>)}
                        </svg>}
                        <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Цена — линия; BUY/SELL — зелёные/красные точки; траллы — фиолетовые. Диапазон {min.toFixed(2)}%…{max.toFixed(2)}% от первой сохранённой цены {basePrice}.</div>
                        <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Сессия: {grid.session_id} · {grid.started_at ? formatTime(grid.started_at) : 'начало не сохранено'}</div>
                    </details>
                })}
            </AppModal>}

            {operations.length === 0 ? (
                <div
                    style={{
                        color:
                        "var(--text-muted)",

                        fontSize:
                        13,
                    }}
                >
                    Операций пока нет: сделки, ордера и действия со счетами появятся здесь.
                </div>
            ) : (
                operations.map(
                    (
                        operation,
                        index,
                    ) => (
                        <div
                            key={
                                operation.created_at
                                + "-"
                                + operation.event_type
                                + "-"
                                + index
                            }

                            style={{
                                display:
                                "flex",

                                justifyContent:
                                "space-between",

                                alignItems:
                                "flex-start",

                                gap:
                                10,

                                padding:
                                "9px 0",

                                borderTop:
                                index
                                === 0
                                ? "none"
                                : "1px solid var(--border)",
                            }}
                        >
                            <div
                                style={{
                                    minWidth:
                                    0,
                                }}
                            >
                                <div
                                    style={{
                                        display:
                                        "flex",

                                        alignItems:
                                        "center",

                                        gap:
                                        8,

                                        marginBottom:
                                        3,
                                    }}
                                >
                                    <span
                                        style={{
                                            fontWeight:
                                            700,

                                            color:
                                            formatEventColor(
                                                operation.event_type
                                            ),

                                            fontSize:
                                            13,
                                        }}
                                    >
                                        {
                                            formatEventType(
                                                operation.event_type
                                            )
                                        }
                                    </span>

                                    {operation.broker && (
                                        <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
                                            {operation.broker === "tinvest" ? "Т-Инвест" : operation.broker === "bybit" ? "Bybit" : operation.broker}
                                        </span>
                                    )}

                                    {
                                        operation.ticker
                                        && (
                                            <span
                                                style={{
                                                    fontWeight:
                                                    700,

                                                    fontSize:
                                                    13,
                                                }}
                                            >
                                                {
                                                    operation.ticker
                                                }
                                            </span>
                                        )
                                    }
                                </div>

                                <div
                                    style={{
                                        color:
                                        "var(--text-muted)",

                                        fontSize:
                                        12,

                                        wordBreak:
                                        "break-word",
                                    }}
                                >
                                    {
                                        operation.details
                                    }
                                </div>
                            </div>

                            <div
                                style={{
                                    color:
                                    "var(--text-dim)",

                                    fontSize:
                                    11,

                                    whiteSpace:
                                    "nowrap",
                                }}
                            >
                                {
                                    formatTime(
                                        operation.created_at
                                    )
                                }
                            </div>
                        </div>
                    )
                )
            )}
        </div>
    )
}
