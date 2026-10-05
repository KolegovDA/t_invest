import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { createRequire } from "node:module"
import test from "node:test"
import { runInNewContext } from "node:vm"
import React from "react"
import { renderToStaticMarkup } from "react-dom/server"
import ts from "typescript"

const require = createRequire(import.meta.url)
const source = readFileSync(new URL("./src/components/DashboardCard.tsx", import.meta.url), "utf8")
const compiled = ts.transpileModule(`${source}\nexport { buildSeries, EquityChart }`, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2020 },
}).outputText
const themeSource = readFileSync(new URL("./src/theme.ts", import.meta.url), "utf8")
const themeCompiled = ts.transpileModule(themeSource, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
}).outputText
const themeExports = {}
const stored = new Map()
const events = []
runInNewContext(themeCompiled, {
    exports: themeExports,
    localStorage: { getItem: key => stored.get(key) ?? null, setItem: (key, value) => stored.set(key, value) },
    window: { dispatchEvent: event => events.push(event.type) }, Event,
})
const exports = {}
runInNewContext(compiled, {
    exports,
    require: name => name === "../api" ? {} : name === "../theme" ? themeExports : require(name),
})
const { buildSeries, EquityChart } = exports
const point = (ts, equity) => ({ ts, equity })
const now = "2026-10-04T12:00:00Z"
const earlier = "2026-10-04T11:00:00Z"
const series = points => [{ label: "Bybit", color: "#f0b90b", points }]
const render = (points, days = 180) => renderToStaticMarkup(React.createElement(EquityChart, {
    series: series(points), days, updatedAt: now,
}))

test("accounts with only a current balance are retained beside historical accounts", () => {
    const result = buildSeries({
        accounts: [{ id: "old", name: "T-Invest" }, { id: "new", name: "Bybit" }],
        points_by_account: { old: [point(earlier, 90), point(now, 100)], new: [point(now, 25)] },
    })
    assert.equal(result.length, 2)
    assert.equal(result[1].label, "Bybit")
    assert.equal(result[1].points.length, 1)
})

test("invalid points are excluded and real points sorted without mutating the response", () => {
    const points = [point(now, 100), point("invalid", 20), point(earlier, 90), point(now, Infinity)]
    const result = buildSeries({ points_by_currency: { USDT: points } })
    assert.equal(result[0].points.length, 2)
    assert.equal(result[0].points[0].ts, earlier)
    assert.equal(points[0].ts, now)
})

test("single currency and legacy current observations remain visible", () => {
    assert.equal(buildSeries({ points_by_currency: { USDT: [point(now, 25)] } })[0].points.length, 1)
    assert.equal(buildSeries({ points: [point(now, 25)] })[0].points.length, 1)
    assert.equal(buildSeries(null).length, 0)
    assert.equal(buildSeries({ points: [point("invalid", 25)] }).length, 0)
})

test("short snapshot history fills the plot instead of collapsing into a 180 day edge", () => {
    const markup = render([point(earlier, 90), point(now, 100)])
    assert.match(markup, /viewBox="0 0 640 220"/)
    assert.match(markup, /d="M72\.00,180\.00 L632\.00,20\.00"/)
    assert.match(markup, /type="range"/)
    assert.doesNotMatch(markup, /NaN|Infinity/)
})

test("a current-only balance is a point, not fabricated historical equity", () => {
    const markup = render([point(now, 25)])
    assert.match(markup, /<circle/)
    assert.match(markup, /d="M632\.00,100\.00"/)
    assert.match(markup, /Пока доступна только текущая оценка/)
    assert.doesNotMatch(markup, /NaN|Infinity/)
})

test("total chart uses converted series and a yellow double-width line", () => {
    const result = buildSeries({
        accounts: [{ id: "a", name: "T-Invest", broker: "tinvest", currency: "RUB" }, { id: "b", name: "Bybit", broker: "bybit", currency: "USDT" }],
        points_by_account: { a: [point(now, 1000)], b: [point(now, 100)] },
        total_points: [point(now, 10000)], total_balance_currency: "RUB", exchange_rates_rub: { RUB: 1, USDT: 90 },
    })
    assert.equal(result[1].points[0].equity, 9000)
    const markup = renderToStaticMarkup(React.createElement(EquityChart, { series: result, days: 7, updatedAt: now }))
    assert.match(markup, /stroke="#facc15" stroke-width="4"/)
    assert.match(markup, /stroke="#22c55e"/)
    assert.match(markup, /stroke="#f59e0b"/)
    assert.match(markup, /height:220px/)
})

test("platform colors persist and reject malformed stored values", () => {
    stored.clear()
    assert.equal(themeExports.getStoredPlatformColors().tinvest, "#f59e0b")
    assert.equal(themeExports.getStoredPlatformColors().bybit, "#22c55e")
    themeExports.storePlatformColors({ tinvest: "#123456", bybit: "#abcdef" })
    assert.equal(themeExports.getStoredPlatformColors().tinvest, "#123456")
    assert.equal(events.at(-1), "esm-platform-colors-changed")
    stored.set("esm-platform-colors", '{"tinvest":"invalid","bybit":"#654321"}')
    assert.equal(themeExports.getStoredPlatformColors().tinvest, "#f59e0b")
    assert.equal(themeExports.getStoredPlatformColors().bybit, "#654321")
    stored.set("esm-platform-colors", "null")
    assert.equal(themeExports.getStoredPlatformColors().bybit, "#22c55e")
})

test("custom platform colors preserve the yellow double-width total", () => {
    const result = buildSeries({
        accounts: [{ id: "a", name: "T-Invest", broker: "tinvest", currency: "RUB" }, { id: "b", name: "Bybit", broker: "bybit", currency: "USDT" }],
        points_by_account: { a: [point(now, 1000)], b: [point(now, 100)] },
        total_points: [point(now, 10000)], total_balance_currency: "RUB", exchange_rates_rub: { RUB: 1, USDT: 90 },
    }, { tinvest: "#123456", bybit: "#abcdef" })
    assert.equal(result[0].color, "#123456")
    assert.equal(result[1].color, "#abcdef")
    const markup = renderToStaticMarkup(React.createElement(EquityChart, { series: result, days: 7, updatedAt: now }))
    assert.match(markup, /stroke="#facc15" stroke-width="4"/)
    assert.match(markup, /stroke="#123456" stroke-width="2"/)
    assert.match(markup, /stroke="#abcdef" stroke-width="2"/)
})

test("total is above platforms in the legend and drawn over them regardless of input order", () => {
    for (const totalFirst of [true, false]) {
        const total = { label: "Общий баланс", color: "#ff0000", points: [point(earlier, 100), point(now, 110)] }
        const platforms = [
            { label: "Т-Инвест", color: "#123456", points: [point(earlier, 50), point(now, 60)] },
            { label: "Bybit", color: "#abcdef", points: [point(earlier, 50), point(now, 50)] },
        ]
        const input = totalFirst ? [total, ...platforms] : [...platforms, total]
        const markup = renderToStaticMarkup(React.createElement(EquityChart, { series: input, days: 7, updatedAt: now }))
        const legend = markup.slice(markup.indexOf('aria-label="Легенда балансов"'), markup.indexOf("<svg"))
        assert.match(legend, /flex-direction:column/)
        assert.ok(legend.indexOf("Общий баланс") < legend.indexOf("Т-Инвест"))
        assert.ok(legend.indexOf("Общий баланс") < legend.indexOf("Bybit"))
        assert.match(legend, /height:4px;background:#facc15/)
        const strokes = [...markup.matchAll(/<path [^>]*stroke="([^"]+)" stroke-width="([^"]+)"/g)]
        assert.deepEqual(strokes.map(match => [match[1], match[2]]), [["#123456", "2"], ["#abcdef", "2"], ["#facc15", "4"]])
        assert.equal(total.color, "#ff0000")
        assert.equal(input[0].label, totalFirst ? "Общий баланс" : "Т-Инвест")
    }
})

test("cabinet commission is shown as a loss and both history event types are labelled as deductions", () => {
    const commissionSource = readFileSync(new URL("./src/components/CommissionCard.tsx", import.meta.url), "utf8")
    const historySource = readFileSync(new URL("./src/components/OperationsHistoryCard.tsx", import.meta.url), "utf8")
    assert.match(commissionSource, /color:\s*"var\(--loss\)",\s*flexShrink:/)
    assert.match(commissionSource, /−\{\s*formatMoney\(\s*charge.amount/)
    const output = ts.transpileModule(`${historySource}\nexport { formatEventType, formatEventColor }`, {
        compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2020 },
    }).outputText
    const history = {}
    runInNewContext(output, { exports: history, require: name => name === "./AppModal" ? {} : require(name) })
    for (const event of ["COMMISSION", "COMMISSION_CHARGED"]) {
        assert.equal(history.formatEventType(event), "Списание комиссии ЛК")
        assert.equal(history.formatEventColor(event), "var(--loss)")
    }
})


test("operations identify both platforms beside the asset without guessing an unknown source", () => {
    const historySource = readFileSync(new URL("./src/components/OperationsHistoryCard.tsx", import.meta.url), "utf8")
    const output = ts.transpileModule(historySource, {
        compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2020 },
    }).outputText
    const history = {}
    runInNewContext(output, { exports: history, require: name => name === "./AppModal" ? {} : require(name) })
    const renderOperations = operations => renderToStaticMarkup(React.createElement(history.OperationsHistoryCard, { operations }))
    const base = { created_at: now, event_type: "BUY", details: "executed", trading_account_id: "a", instrument_id: "id" }
    const markup = renderOperations([{ ...base, broker: "tinvest", ticker: "SMLT" }, { ...base, broker: "bybit", ticker: "ETHUSDT" }])
    assert.match(markup, /Т-Инвест/)
    assert.match(markup, /SMLT/)
    assert.match(markup, /Bybit/)
    assert.match(markup, /ETHUSDT/)
    assert.doesNotMatch(renderOperations([{ ...base, broker: null, ticker: "UNKNOWN" }]), /Т-Инвест|Bybit/)
})

test("profile precedes settings and user data is not duplicated in settings", () => {
    const navigation = readFileSync(new URL("./src/components/BottomNavigation.tsx", import.meta.url), "utf8")
    const app = readFileSync(new URL("./src/App.tsx", import.meta.url), "utf8")
    assert.ok(navigation.indexOf('tab: "profile"') < navigation.indexOf('tab: "settings"'))
    assert.match(app, /activeTab === "profile" && <UserSettingsCard/)
    const settings = app.slice(app.indexOf('{activeTab === "settings"'), app.indexOf("<BottomNavigation"))
    assert.doesNotMatch(settings, /<UserSettingsCard/)
})

test("charts on the same page have independent clipping identifiers", () => {
    const props = { series: series([point(earlier, 90), point(now, 100)]), days: 7, updatedAt: now }
    const markup = renderToStaticMarkup(React.createElement("div", null,
        React.createElement(EquityChart, props), React.createElement(EquityChart, props)))
    const ids = [...markup.matchAll(/<clipPath id="([^"]+)"/g)].map(match => match[1])
    assert.equal(ids.length, 2)
    assert.notEqual(ids[0], ids[1])
})
