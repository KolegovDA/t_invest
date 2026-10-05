import { useEffect, useRef, useState } from "react"
import type { CSSProperties } from "react"
import { getSelectionOptions, previewAutoSelection, previewGridSelection, previewIndexSelection, searchInstruments } from "../api"
import { InstrumentCard } from "./InstrumentCard"
import type { GridSelectionPlan, Instrument, InstrumentSearchResult, SelectionOptions } from "../types"

type TabMode = "index" | "manual" | "auto"
type CandidateForm = { ticker: string; levels: string; quantity: string }
type SelectedInstrument = Instrument & { name?: string; volatility_percent?: string; risk_band?: string }
const formatAmount = (value: string | number) => Number(value).toLocaleString("ru-RU", { maximumFractionDigits: 2 })
const inputStyle: CSSProperties = { flex: 1, minWidth: 60, padding: 10, borderRadius: 10, border: "1px solid var(--border)", fontSize: 14 }
const buttonStyle: CSSProperties = { padding: 12, borderRadius: 10, border: "1px solid var(--border)", background: "var(--accent)", color: "white", fontWeight: 700, cursor: "pointer" }
const candidateDefaults = (): CandidateForm => ({ ticker: "", levels: "30", quantity: "1" })
const toInstrument = (item: GridSelectionPlan["selections"][number]): SelectedInstrument => ({
    ticker: item.ticker, levels: item.levels, quantity: item.quantity, name: item.name,
    price: Number(item.price), required_capital: Number(item.estimated_cost),
    volatility_percent: item.volatility_percent, risk_band: item.risk_band,
})

export function InstrumentSelectionCard({ onSelect, tradingAccountId }: {
    onSelect?: (instruments: Instrument[]) => void
    tradingAccountId?: string | null
}) {
    const version = useRef(0)
    const [tab, setTab] = useState<TabMode>("index")
    const [capital, setCapital] = useState("100000")
    const [quantity, setQuantity] = useState("1")
    const [options, setOptions] = useState<SelectionOptions | null>(null)
    const [selectedIndexId, setSelectedIndexId] = useState("blue_chips")
    const [autoMaxInstruments, setAutoMaxInstruments] = useState(5)
    const [autoMaxPrice, setAutoMaxPrice] = useState("")
    const [candidates, setCandidates] = useState<CandidateForm[]>([candidateDefaults()])
    const [activeSearchIndex, setActiveSearchIndex] = useState<number | null>(null)
    const [searchResults, setSearchResults] = useState<InstrumentSearchResult[]>([])
    const [isSearching, setIsSearching] = useState(false)
    const [searchError, setSearchError] = useState<string | null>(null)
    const [plan, setPlan] = useState<GridSelectionPlan | null>(null)
    const [selectedInstruments, setSelectedInstruments] = useState<SelectedInstrument[]>([])
    const [selectionCapital, setSelectionCapital] = useState("0")
    const [selectionReady, setSelectionReady] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [isCalculating, setIsCalculating] = useState(false)
    const [addedTicker, setAddedTicker] = useState("")
    const [addedLevels, setAddedLevels] = useState("30")
    const [addedQuantity, setAddedQuantity] = useState("1")
    const [addedSearchActive, setAddedSearchActive] = useState(false)
    const [editingTicker, setEditingTicker] = useState<string | null>(null)

    useEffect(() => {
        let cancelled = false
        getSelectionOptions().then(result => { if (!cancelled) setOptions(result) }).catch(() => {})
        return () => { cancelled = true; version.current += 1 }
    }, [])
    const searchQuery = addedSearchActive ? addedTicker.trim()
        : tab === "manual" && activeSearchIndex !== null ? candidates[activeSearchIndex]?.ticker.trim() ?? "" : ""
    useEffect(() => {
        setSearchResults([])
        setSearchError(null)
        if (!searchQuery || !tradingAccountId) { setIsSearching(false); return }
        let cancelled = false
        setIsSearching(true)
        const timer = setTimeout(() => {
            searchInstruments(searchQuery, tradingAccountId, 30)
                .then(result => { if (!cancelled) setSearchResults(result.instruments) })
                .catch(failure => { if (!cancelled) setSearchError(failure instanceof Error ? failure.message : String(failure)) })
                .finally(() => { if (!cancelled) setIsSearching(false) })
        }, 250)
        return () => { cancelled = true; clearTimeout(timer) }
    }, [searchQuery, activeSearchIndex, addedSearchActive, tradingAccountId, tab])

    const selectedCost = selectedInstruments.reduce((total, item) => total + item.required_capital, 0)
    const selectedRemaining = Number(selectionCapital) - selectedCost
    function updateCandidate(index: number, patch: Partial<CandidateForm>) {
        setCandidates(current => current.map((item, position) => position === index ? { ...item, ...patch } : item))
    }
    function changeTab(mode: TabMode) {
        if (tab === mode) return
        version.current += 1
        setTab(mode)
        setIsCalculating(false)
        setPlan(null)
        setSelectedInstruments([])
        setSelectionReady(false)
        setActiveSearchIndex(null)
        setAddedSearchActive(false)
        setEditingTicker(null)
        setAddedTicker("")
        setError(null)
    }
    function gridInput(ticker: string, levels: string, units: string) {
        const count = Number(levels)
        const baseQuantity = Number(units)
        if (!ticker.trim() || !Number.isInteger(count) || count < 5 || count > 30 || !Number.isInteger(baseQuantity) || baseQuantity < 1) {
            throw new Error("Укажите тикер, от 5 до 30 уровней и целое количество лотов больше нуля.")
        }
        return { ticker: ticker.trim().toUpperCase(), levels: count, quantity: baseQuantity }
    }
    async function calculate(mode: TabMode) {
        const capitalValue = capital.trim()
        if (!Number.isFinite(Number(capitalValue)) || Number(capitalValue) <= 0) { setError("Укажите капитал больше нуля."); return }
        const requestVersion = ++version.current
        setIsCalculating(true)
        setSelectionReady(false)
        setSelectedInstruments([])
        setPlan(null)
        setError(null)
        try {
            let result: GridSelectionPlan
            if (mode === "manual") {
                const filled = candidates.filter(item => item.ticker.trim())
                if (!filled.length) throw new Error("Добавьте хотя бы один инструмент.")
                const instruments = filled.map(item => gridInput(item.ticker, item.levels, item.quantity))
                if (new Set(instruments.map(item => item.ticker)).size !== instruments.length) throw new Error("Уберите дублирующиеся инструменты.")
                result = await previewGridSelection({ capital: capitalValue, instruments, trading_account_id: tradingAccountId })
            } else {
                const units = gridInput("CHECK", "30", quantity).quantity
                result = mode === "index"
                    ? await previewIndexSelection({ capital: capitalValue, index_id: selectedIndexId, quantity: units, trading_account_id: tradingAccountId })
                    : await previewAutoSelection({ capital: capitalValue, quantity: units, max_instruments: autoMaxInstruments, max_price: autoMaxPrice.trim() || null, trading_account_id: tradingAccountId })
            }
            if (requestVersion !== version.current) return
            setPlan(result)
            setSelectionCapital(result.capital ?? capitalValue)
            setSelectedInstruments(result.selections.map(toInstrument))
            setSelectionReady(true)
        } catch (failure) {
            if (requestVersion === version.current) setError(failure instanceof Error ? failure.message : String(failure))
        } finally {
            if (requestVersion === version.current) setIsCalculating(false)
        }
    }
    function configureSelectedInstrument(instrument: Instrument) {
        setEditingTicker(instrument.ticker)
        setAddedTicker(instrument.ticker)
        setAddedLevels(String(instrument.levels))
        setAddedQuantity(String(instrument.quantity))
        setAddedSearchActive(false)
        setActiveSearchIndex(null)
    }
    async function saveSelectedInstrument() {
        const requestVersion = ++version.current
        setIsCalculating(true)
        setError(null)
        try {
            const input = gridInput(addedTicker, addedLevels, addedQuantity)
            if (selectedInstruments.some(item => item.ticker === input.ticker && item.ticker !== editingTicker)) throw new Error(`Инструмент ${input.ticker} уже добавлен.`)
            const result = await previewGridSelection({ capital: selectionCapital, instruments: [input], trading_account_id: tradingAccountId })
            if (requestVersion !== version.current) return
            const item = result.selections.find(value => value.ticker === input.ticker)
            if (!item || !Number.isFinite(Number(item.estimated_cost)) || !Number.isFinite(Number(item.price)) || Number(item.price) <= 0) throw new Error("Не удалось рассчитать сетку инструмента.")
            const available = selectedRemaining + (selectedInstruments.find(value => value.ticker === editingTicker)?.required_capital ?? 0)
            if (Number(item.estimated_cost) > available) throw new Error(`Не хватает капитала: нужно ${formatAmount(item.estimated_cost)} ₽, доступно ${formatAmount(available)} ₽.`)
            const instrument = toInstrument(item)
            setSelectedInstruments(current => editingTicker ? current.map(value => value.ticker === editingTicker ? instrument : value) : [...current, instrument])
            setEditingTicker(null)
            setAddedTicker("")
            setAddedSearchActive(false)
        } catch (failure) {
            if (requestVersion === version.current) setError(failure instanceof Error ? failure.message : String(failure))
        } finally {
            if (requestVersion === version.current) setIsCalculating(false)
        }
    }
    const results = (onSelectResult: (item: InstrumentSearchResult) => void) => <div aria-live="polite">
        {isSearching && <div>Поиск инструментов...</div>}
        {searchError && <div role="alert">{searchError}</div>}
        {!isSearching && !searchError && searchQuery && searchResults.length === 0 && <div>Совпадения не найдены.</div>}
        {searchResults.map(item => <button key={item.instrument_uid} type="button" disabled={isCalculating} onClick={() => onSelectResult(item)}
            style={{ width: "100%", padding: 8, textAlign: "left", border: "1px solid var(--border)", background: "var(--card)", color: "var(--text)" }}>
            <b>{item.ticker}</b> · {item.name} · Лот: {item.lot_size} · {item.currency.toUpperCase()}
        </button>)}
    </div>

    return <div style={{ background: "var(--card)", borderRadius: 16, padding: 16, marginBottom: 16 }}>
        <h2>Подбор инструментов</h2>
        <p style={{ fontSize: 13, color: "var(--text-muted)" }}>Индекс и авто подбирают сетки в бюджет. В ручном режиме выбирайте активы и параметры сеток самостоятельно, без рейтинговых фильтров.</p>
        <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
            {(["index", "manual", "auto"] as const).map(mode => <button key={mode} type="button" onClick={() => changeTab(mode)} style={{ ...buttonStyle, flex: 1, background: mode === tab ? "var(--accent)" : "var(--card)", color: mode === tab ? "white" : "var(--text)" }}>{mode === "index" ? "Индекс" : mode === "manual" ? "Ручной" : "Авто"}</button>)}
        </div>
        <label>Бюджет, ₽ <input aria-label="Бюджет подбора" style={inputStyle} value={capital} disabled={isCalculating} inputMode="decimal" onChange={event => setCapital(event.target.value)} /></label>
        {tab !== "manual" && <label> Лотов в уровень <input style={inputStyle} value={quantity} inputMode="numeric" onChange={event => setQuantity(event.target.value)} /></label>}
        {tab === "index" && <div style={{ marginTop: 12 }}>
            <select style={inputStyle} value={selectedIndexId} onChange={event => setSelectedIndexId(event.target.value)}>{(options?.indexes ?? []).map(index => <option key={index.index_id} value={index.index_id}>{index.name} · {index.tickers_count} шт.</option>)}</select>
            <p>Сетка от 5 до 30 уровней подбирается в остаток бюджета; слишком дорогие бумаги пропускаются.</p>
            <button style={buttonStyle} disabled={isCalculating} onClick={() => calculate("index")}>Рассчитать индекс</button>
        </div>}
        {tab === "auto" && <div style={{ marginTop: 12 }}>
            <label>Максимум активов <input style={inputStyle} inputMode="numeric" value={autoMaxInstruments} onChange={event => setAutoMaxInstruments(Math.max(1, Number(event.target.value)))} /></label>
            <label>Максимальная цена <input style={inputStyle} inputMode="decimal" value={autoMaxPrice} onChange={event => setAutoMaxPrice(event.target.value)} /></label>
            <p>Самые волатильные акции; сетка от 5 до 30 уровней в пределах бюджета.</p>
            <button style={buttonStyle} disabled={isCalculating} onClick={() => calculate("auto")}>Рассчитать авторежим</button>
        </div>}
        {tab === "manual" && <div style={{ marginTop: 12 }}>
            {candidates.map((item, index) => <div key={index} style={{ marginBottom: 12 }}>
                <input aria-label={`Тикер или название актива ${index + 1}`} style={{ ...inputStyle, width: "100%", boxSizing: "border-box" }} value={item.ticker} disabled={isCalculating} placeholder="Тикер или название" onChange={event => {
                    updateCandidate(index, { ticker: event.target.value }); setActiveSearchIndex(index); setAddedSearchActive(false); setSearchResults([])
                }} />
                {activeSearchIndex === index && results(value => { updateCandidate(index, { ticker: value.ticker }); setActiveSearchIndex(null); setSearchResults([]) })}
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 8 }}>
                    <label>Уровни (5–30) <input aria-label={`Уровни актива ${index + 1}`} style={inputStyle} value={item.levels} inputMode="numeric" disabled={isCalculating} onChange={event => updateCandidate(index, { levels: event.target.value })} /></label>
                    <label>Лотов в уровень <input aria-label={`Лотов в уровень актива ${index + 1}`} style={inputStyle} value={item.quantity} inputMode="numeric" disabled={isCalculating} onChange={event => updateCandidate(index, { quantity: event.target.value })} /></label>
                    <button type="button" disabled={isCalculating} onClick={() => { setCandidates(current => current.filter((_, position) => position !== index)); setActiveSearchIndex(null) }}>Убрать</button>
                </div>
            </div>)}
            <button type="button" disabled={isCalculating} onClick={() => setCandidates(current => [...current, candidateDefaults()])}>+ Инструмент</button>
            <button style={buttonStyle} disabled={isCalculating} onClick={() => calculate("manual")}>Рассчитать портфель</button>
        </div>}
        {error && <div role="alert" style={{ marginTop: 12, color: "var(--loss)" }}>{error}</div>}
        {isCalculating && <div aria-live="polite">Расчёт...</div>}
        {selectionReady && <div style={{ marginTop: 12 }}>
            <h3>Выбранные активы</h3>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 12, marginBottom: 12 }}><b>Потрачено: {formatAmount(selectedCost)} ₽</b><b>Остаток: {formatAmount(selectedRemaining)} ₽</b></div>
            {selectedInstruments.map(instrument => <InstrumentCard key={instrument.ticker} instrument={instrument} name={instrument.name} volatilityPercent={instrument.volatility_percent} riskBand={instrument.risk_band} disabled={isCalculating} onConfigure={configureSelectedInstrument} onRemove={ticker => { setSelectedInstruments(current => current.filter(item => item.ticker !== ticker)); setError(null) }} />)}
            <h4>{editingTicker ? `Настройка ${editingTicker}` : "Добавить актив вручную"}</h4>
            <input aria-label="Тикер или название дополнительного актива" style={{ ...inputStyle, width: "100%", boxSizing: "border-box" }} value={addedTicker} disabled={isCalculating || editingTicker !== null} onChange={event => { setAddedTicker(event.target.value); setAddedSearchActive(true); setActiveSearchIndex(null); setSearchResults([]) }} />
            {addedSearchActive && results(item => { setAddedTicker(item.ticker); setAddedSearchActive(false); setSearchResults([]) })}
            <label>Уровни (5–30) <input aria-label="Уровни дополнительного актива" style={inputStyle} inputMode="numeric" value={addedLevels} disabled={isCalculating} onChange={event => setAddedLevels(event.target.value)} /></label>
            <label>Лотов в уровень <input aria-label="Штук в уровень дополнительного актива" style={inputStyle} inputMode="numeric" value={addedQuantity} disabled={isCalculating} onChange={event => setAddedQuantity(event.target.value)} /></label>
            <button style={buttonStyle} disabled={isCalculating || !addedTicker.trim()} onClick={saveSelectedInstrument}>{editingTicker ? "Сохранить параметры актива" : "Добавить актив в подбор"}</button>
            {editingTicker && <button disabled={isCalculating} onClick={() => { setEditingTicker(null); setAddedTicker("") }}>Отменить настройку</button>}
            {selectedRemaining < 0 && <div role="alert">Не хватает капитала: нужно {formatAmount(selectedCost)} ₽, доступно {formatAmount(selectionCapital)} ₽. Уберите актив или уменьшите сетку.</div>}
            {onSelect && selectedInstruments.length > 0 && <button style={{ ...buttonStyle, width: "100%", marginTop: 12 }} disabled={isCalculating || selectedRemaining < 0} onClick={() => onSelect(selectedInstruments)}>Добавить выбранные инструменты</button>}
        </div>}
        {plan && plan.rejected?.length > 0 && <div style={{ marginTop: 12 }}><b>Не включены в автоматический подбор:</b>{plan.rejected.map((item, index) => <div key={`${item.ticker}-${index}`}>{item.ticker} — {item.reason}</div>)}</div>}
    </div>
}
