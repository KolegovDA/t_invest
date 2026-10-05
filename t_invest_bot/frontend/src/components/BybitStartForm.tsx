import {useState} from "react"
import {startLive} from "../api"
import type {TradingAccount} from "../accounts/types"

const PRESETS = ["ETHUSDT", "XRPUSDT", "BTCUSDT", "LINKUSDT", "TONUSDT", "DOTUSDT", "BNBUSDT", "SOLUSDT", "LTCUSDT", "DOGEUSDT", "ARBUSDT", "MNTUSDT", "AVAXUSDT"]

type Props = {
    accounts: TradingAccount[]
    onStarted: () => void
}

export function BybitStartForm({accounts, onStarted}: Props) {
    const [accountId, setAccountId] = useState(accounts[0]?.id ?? "")
    const [automatic, setAutomatic] = useState(true)
    const [symbols, setSymbols] = useState(["ETHUSDT"])
    const [custom, setCustom] = useState("")
    const [levels, setLevels] = useState(20)
    const [amounts, setAmounts] = useState<Record<string, string>>({})
    const [error, setError] = useState<string | null>(null)
    const [busy, setBusy] = useState(false)

    async function start() {
        setBusy(true)
        setError(null)
        try {
            if (!accountId || symbols.length === 0) throw new Error("Выберите счёт и активы")
            if (!automatic && symbols.some(symbol => !Number.isFinite(Number(amounts[symbol] ?? "6")) || Number(amounts[symbol] ?? "6") <= 0)) throw new Error("Введите положительную сумму ордера")
            await startLive(false, symbols.map(ticker => ({ticker, levels, quantity: 1, base_order_amount: automatic ? undefined : Number(amounts[ticker] ?? "6")})), accountId, automatic)
            onStarted()
        } catch (e) {
            setError(e instanceof Error ? e.message : String(e))
        } finally {
            setBusy(false)
        }
    }

    return <div style={{display: "grid", gap: 12}}>
        <label>Боевой счёт Bybit<select value={accountId} onChange={event => setAccountId(event.target.value)} style={{width: "100%"}}>
            <option value="">Выберите счёт</option>
            {accounts.map(account => <option key={account.id} value={account.id}>{account.name}</option>)}
        </select></label>
        <label>Режим<select value={automatic ? "auto" : "manual"} onChange={event => setAutomatic(event.target.value === "auto")}>
            <option value="auto">Автоматический</option><option value="manual">Ручной</option>
        </select></label>
        {automatic && <div>От 200 USDT. Начальный ордер: 3% доступного USDT-баланса (200 → 6, 300 → 9). Ограничения биржи и фактическая комиссия проверяются отдельно для каждого актива.</div>}
        <label>Количество уровней<input type="number" min={2} max={1000} value={levels} onChange={event => setLevels(Number(event.target.value))}/></label>
        <button type="button" onClick={() => setSymbols([...PRESETS])}>Включить встроенный набор валют</button>
        {PRESETS.map(symbol => <label key={symbol}><input type="checkbox" checked={symbols.includes(symbol)} onChange={event => setSymbols(event.target.checked ? [...symbols, symbol] : symbols.filter(item => item !== symbol))}/>{symbol}</label>)}
        <div><input value={custom} placeholder="Другой USDT-актив" onChange={event => setCustom(event.target.value.toUpperCase())}/><button type="button" onClick={() => {if (custom.trim() && !symbols.includes(custom.trim())) setSymbols([...symbols, custom.trim()]); setCustom("")}}>Добавить</button></div>
        {!automatic && symbols.map(symbol => <label key={symbol}>{symbol}: начальная сумма покупки, USDT<input type="number" min="0.0001" step="any" value={amounts[symbol] ?? "6"} onChange={event => setAmounts({...amounts, [symbol]: event.target.value})}/></label>)}
        <div>Рост суммы, TP и траллы берутся из индивидуальных настроек головы. Используется основная стратегия; её шаг сетки фиксированный.</div>
        {error && <div role="alert" style={{color: "var(--danger)"}}>{error}</div>}
        <button type="button" disabled={busy || !accountId || symbols.length === 0} onClick={start}>{busy ? "Проверка и запуск..." : "Запустить Bybit"}</button>
    </div>
}
