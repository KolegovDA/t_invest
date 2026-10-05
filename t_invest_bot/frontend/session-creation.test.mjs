import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { createRequire } from "node:module"
import test from "node:test"
import { runInNewContext } from "node:vm"
import ts from "typescript"

const source = readFileSync(new URL("./src/App.tsx", import.meta.url), "utf8")

test("registration is offered only for an installation without a user", async () => {
    const authSource = readFileSync(new URL("./src/components/AuthScreen.tsx", import.meta.url), "utf8")
    const output = ts.transpileModule(authSource, {
        compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2020 },
    }).outputText
    for (const hasUsers of [true, false]) {
        const state = []
        let index = 0
        let effectRun = false
        const authExports = {}
        runInNewContext(output, {
            exports: authExports,
            require: name => name === "react" ? {
                useState: initial => {
                    const position = index++
                    if (!(position in state)) state[position] = initial
                    return [state[position], value => { state[position] = value }]
                },
                useEffect: callback => { if (!effectRun) { effectRun = true; callback() } },
            } : name === "../api" ? { getAuthStatus: async () => ({ has_users: hasUsers, device_has_pin: false }) }
                : name === "../auth/security" ? { getDeviceId: () => "browser" } : require(name),
        })
        const render = () => {
            index = 0
            return authExports.AuthScreen({ initialMode: "register", onAuthenticated: () => {} })
        }
        render()
        await new Promise(resolve => setImmediate(resolve))
        const tree = render()
        assert.equal(state[0], hasUsers ? "login" : "register")
        assert.equal(state[1].has_users, hasUsers)
        assert.equal(findElement(tree, item => item.type === "button" && item.props.children === "Создать аккаунт этой установки"), undefined)
        assert.equal(Boolean(findElement(tree, item => item.type === "button" && item.props.children === "Уже есть аккаунт — войти")), !hasUsers)
    }
})


test("new session opens with no preselected platform and resets prior instrument selection", () => {
    assert.match(source, /const \[startPlatform, setStartPlatform\] = useState\(""\)/)
    const handler = source.slice(source.indexOf("function openNewSession()"), source.indexOf("function changeSessionPlatform"))
    assert.match(handler, /setStartPlatform\(""\)/)
    assert.match(handler, /setInstruments\(\[\]\)/)
    assert.match(handler, /setSelectionOpen\(true\)/)
    assert.match(source, /onClick=\{openNewSession\}/)
})

test("platform selection is displayed before any platform-specific instrument form", () => {
    const creation = source.slice(source.indexOf('{selectionOpen && ('), source.indexOf('{accountsOpen && ('))
    assert.ok(creation.indexOf('aria-label="Платформа новой сессии"') < creation.indexOf("<BybitStartForm"))
    assert.ok(creation.indexOf('startPlatform === "tinvest"') < creation.indexOf("Подбор инструментов"))
    assert.match(creation, /startPlatform === "bybit" && <BybitStartForm/)
    assert.match(creation, /selectedTradingAccountId && <div/)
})

test("changing platform or account clears incompatible instruments and validation", () => {
    for (const name of ["changeSessionPlatform", "changeSessionAccount"]) {
        const handler = source.slice(source.indexOf(`function ${name}(`)) .split("\n    }")[0]
        assert.match(handler, /setInstruments\(\[\]\)/)
        assert.match(handler, /resetValidation\(\)/)
    }
})

test("upper account cards receive sessions and the old lower cards remain", () => {
    assert.match(source, /<OverviewAccountsCard overview=\{overview\} sessions=\{sessions\} onOpenTicker=\{openSession\}/)
    assert.match(source, /<TradingOverviewCard overview=\{overview\} sessions=\{sessions\} onOpenTicker=\{openSession\}/)
    const accounts = readFileSync(new URL("./src/components/AccountsOverviewCard.tsx", import.meta.url), "utf8")
    assert.match(accounts, /<TradingAccountDetails account=\{account\} sessions=\{sessions\} onOpenTicker=\{onOpenTicker\}/)
})

const require = createRequire(import.meta.url)
const selectionSource = readFileSync(new URL("./src/components/InstrumentSelectionCard.tsx", import.meta.url), "utf8")
const compiledSelection = ts.transpileModule(selectionSource, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2020 },
}).outputText

function createSelectionHarness(searchInstruments, api = {}) {
    const state = []
    const refs = []
    let stateIndex = 0
    let refIndex = 0
    const effectDependencies = []
    let effectIndex = 0
    let effects = []
    const cleanups = []
    let timers = []
    const exports = {}
    runInNewContext(compiledSelection, {
        exports,
        Error,
        require: name => name === "react" ? {
            useState: initial => {
                const index = stateIndex++
                if (!(index in state)) state[index] = initial
                return [state[index], value => { state[index] = typeof value === "function" ? value(state[index]) : value }]
            },
            useRef: initial => {
                const index = refIndex++
                if (!(index in refs)) refs[index] = { current: initial }
                return refs[index]
            },
            useEffect: (effect, dependencies) => {
                const index = effectIndex++
                const previous = effectDependencies[index]
                if (!previous || dependencies.some((value, position) => !Object.is(value, previous[position]))) {
                    effectDependencies[index] = dependencies
                    effects.push(() => {
                        cleanups[index]?.()
                        cleanups[index] = effect()
                    })
                }
            },
        } : name === "../api" ? {
            getSelectionOptions: async () => ({ indexes: [], auto: { universe_tickers_count: 40 }, defaults: { desired_levels: 30, min_levels: 5 } }),
            searchInstruments,
            ...api,
        } : name === "./InstrumentCard" ? { InstrumentCard: "InstrumentCard" } : require(name),
        setTimeout: callback => { timers.push(callback); return callback },
        clearTimeout: callback => { timers = timers.filter(timer => timer !== callback) },
    })
    return {
        render(account = "account-7", onSelect = undefined) {
            effects = []
            stateIndex = 0
            refIndex = 0
            effectIndex = 0
            const tree = exports.InstrumentSelectionCard({ tradingAccountId: account, onSelect })
            effects.forEach(effect => effect())
            return tree
        },
        async flush() {
            timers.splice(0).forEach(timer => timer())
            await new Promise(resolve => setImmediate(resolve))
        },
    }
}

function findElement(tree, predicate) {
    if (!tree || typeof tree !== "object") return undefined
    if (Array.isArray(tree)) return tree.map(item => findElement(item, predicate)).find(Boolean)
    if (predicate(tree)) return tree
    return findElement(tree.props?.children, predicate)
}

function openManualSearch(harness, query) {
    const tree = harness.render()
    findElement(tree, item => item.type === "button" && item.props.children === "Ручной").props.onClick()
    const manual = harness.render()
    findElement(manual, item => item.props?.["aria-label"] === "Тикер или название актива 1")
        .props.onChange({ target: { value: query } })
    harness.render()
}

for (const query of ["Сбербанк", "SBER"]) {
    test(`manual selection searches the broker catalogue by ${query} with the selected account`, async () => {
        const calls = []
        const harness = createSelectionHarness(async (...args) => {
            calls.push(args)
            return { instruments: [{ instrument_uid: "sber-uid", ticker: "SBER", name: "Сбербанк", lot_size: 10, currency: "rub" }] }
        })
        openManualSearch(harness, query)
        await harness.flush()
        assert.deepEqual(calls, [[query, "account-7", 30]])
        const results = harness.render()
        findElement(results, item => item.type === "button" && item.key === "sber-uid").props.onClick()
        const selected = harness.render()
        assert.equal(findElement(selected, item => item.props?.["aria-label"] === "Тикер или название актива 1").props.value, "SBER")
        assert.equal(findElement(selected, item => item.key === "sber-uid"), undefined)
    })
}

test("outdated catalogue replies cannot replace results for a newer query", async () => {
    let resolveOld
    const harness = createSelectionHarness(query => query === "Сбер" ? new Promise(resolve => { resolveOld = resolve }) : Promise.resolve({
        instruments: [{ instrument_uid: "gazp-uid", ticker: "GAZP", name: "Газпром", lot_size: 10, currency: "rub" }],
    }))
    openManualSearch(harness, "Сбер")
    await harness.flush()
    const old = harness.render()
    findElement(old, item => item.props?.["aria-label"] === "Тикер или название актива 1").props.onChange({ target: { value: "Газпром" } })
    harness.render()
    await harness.flush()
    resolveOld({ instruments: [{ instrument_uid: "sber-uid", ticker: "SBER", name: "Сбербанк", lot_size: 10, currency: "rub" }] })
    await harness.flush()
    const results = harness.render()
    assert.ok(findElement(results, item => item.key === "gazp-uid"))
    assert.equal(findElement(results, item => item.key === "sber-uid"), undefined)
})

test("catalogue failures are visible and selecting a new account remounts the selection form", async () => {
    const harness = createSelectionHarness(async () => { throw new Error("Каталог недоступен") })
    openManualSearch(harness, "SBER")
    await harness.flush()
    assert.equal(findElement(harness.render(), item => item.props?.role === "alert").props.children, "Каталог недоступен")
    assert.match(source, /<InstrumentSelectionCard key=\{selectedTradingAccountId\} tradingAccountId=\{selectedTradingAccountId\}/)
})

const gridPlan = () => ({
    mode: "index", capital: "100000", spent_capital: "30000.1234", remaining_capital: "69999.8766", rejected: [],
    selections: [
        { ticker: "SBER", levels: 30, quantity: 1, price: "100.1234", estimated_cost: "10000.1234" },
        { ticker: "GAZP", levels: 30, quantity: 1, price: "200", estimated_cost: "20000" },
    ],
})

const findButton = (tree, label) => findElement(tree, item => item.type === "button" && item.props.children === label)
const findCard = (tree, ticker) => findElement(tree, item => item.type === "InstrumentCard" && item.props.instrument.ticker === ticker)

function textContent(tree) {
    if (tree === null || tree === undefined || typeof tree === "boolean") return ""
    if (typeof tree === "string" || typeof tree === "number") return String(tree)
    if (Array.isArray(tree)) return tree.map(textContent).join("")
    return textContent(tree.props?.children)
}

async function calculateSelection(harness, mode = "index") {
    if (mode !== "index") {
        findButton(harness.render(), mode === "auto" ? "Авто" : "Ручной").props.onClick()
    }
    await findButton(harness.render(), mode === "index" ? "Рассчитать индекс" : "Рассчитать авторежим").props.onClick()
}

for (const mode of ["index", "auto"]) {
    test(`${mode} selection removes cards, updates totals and applies only remaining assets`, async () => {
        const requests = []
        const preview = async request => { requests.push(request); return gridPlan() }
        const harness = createSelectionHarness(async () => ({ instruments: [] }), {
            previewIndexSelection: preview, previewAutoSelection: preview,
        })
        await calculateSelection(harness, mode)
        assert.equal(requests[0].trading_account_id, "account-7")
        let tree = harness.render()
        assert.ok(findCard(tree, "SBER"))
        assert.match(textContent(tree), /30\s000,12/)
        findCard(tree, "SBER").props.onRemove("SBER")
        let applied
        tree = harness.render("account-7", value => { applied = value })
        assert.equal(findCard(tree, "SBER"), undefined)
        assert.match(textContent(tree), /Потрачено: 20\s000 ₽/)
        assert.match(textContent(tree), /Остаток: 80\s000 ₽/)
        findButton(tree, "Добавить выбранные инструменты").props.onClick()
        assert.deepEqual(Array.from(applied, item => item.ticker), ["GAZP"])
    })
}

test("manual additions use catalogue search, retain selected assets and reject duplicates and over-budget grids", async () => {
    const searchCalls = []
    const calculations = []
    let deposit = "1000.1234"
    const harness = createSelectionHarness(async (...args) => {
        searchCalls.push(args)
        return { instruments: [{ instrument_uid: "lkoh-uid", ticker: "LKOH", name: "Лукойл", lot_size: 1, currency: "rub" }] }
    }, {
        previewIndexSelection: async () => gridPlan(),
        previewGridSelection: async request => {
            calculations.push(request)
            return { selections: [{ ...request.instruments[0], price: "123.4567", estimated_cost: deposit }] }
        },
    })
    await calculateSelection(harness)
    let tree = harness.render()
    findElement(tree, item => item.props?.["aria-label"] === "Тикер или название дополнительного актива")
        .props.onChange({ target: { value: "Лукойл" } })
    harness.render()
    await harness.flush()
    assert.deepEqual(searchCalls, [["Лукойл", "account-7", 30]])
    findElement(harness.render(), item => item.key === "lkoh-uid").props.onClick()
    await findButton(harness.render(), "Добавить актив в подбор").props.onClick()
    tree = harness.render()
    assert.ok(findCard(tree, "SBER"))
    assert.ok(findCard(tree, "GAZP"))
    assert.equal(findCard(tree, "LKOH").props.instrument.required_capital, 1000.1234)
    assert.equal(calculations[0].trading_account_id, "account-7")
    assert.equal(calculations[0].capital, "100000")
    findElement(tree, item => item.props?.["aria-label"] === "Тикер или название дополнительного актива")
        .props.onChange({ target: { value: "LKOH" } })
    await findButton(harness.render(), "Добавить актив в подбор").props.onClick()
    assert.equal(calculations.length, 1)
    assert.match(textContent(harness.render()), /уже добавлен/)
    findElement(harness.render(), item => item.props?.["aria-label"] === "Тикер или название дополнительного актива")
        .props.onChange({ target: { value: "ROSN" } })
    deposit = "90000.9876"
    await findButton(harness.render(), "Добавить актив в подбор").props.onClick()
    tree = harness.render()
    assert.equal(findCard(tree, "ROSN"), undefined)
    assert.match(textContent(tree), /нужно 90\s000,99 ₽, доступно 68\s999,75 ₽/)
})

test("selected grid settings are recalculated and replacement frees its previous cost", async () => {
    const harness = createSelectionHarness(async () => ({ instruments: [] }), {
        previewIndexSelection: async () => gridPlan(),
        previewGridSelection: async request => ({
            selections: [{ ...request.instruments[0], price: "100", estimated_cost: "5000" }],
        }),
    })
    await calculateSelection(harness)
    findCard(harness.render(), "SBER").props.onConfigure(findCard(harness.render(), "SBER").props.instrument)
    let tree = harness.render()
    findElement(tree, item => item.props?.["aria-label"] === "Уровни дополнительного актива").props.onChange({ target: { value: "5" } })
    await findButton(harness.render(), "Сохранить параметры актива").props.onClick()
    tree = harness.render()
    assert.equal(findCard(tree, "SBER").props.instrument.levels, 5)
    assert.equal(findCard(tree, "SBER").props.instrument.required_capital, 5000)
    assert.match(textContent(tree), /Остаток: 75\s000 ₽/)
})

test("manual portfolio calculation produces actionable asset cards", async () => {
    const harness = createSelectionHarness(async () => ({ instruments: [] }), {
        previewInstrumentSelection: async () => { throw new Error("Legacy filters must not run") },
        previewGridSelection: async request => ({ selections: [{ ...request.instruments[0], price: "100", estimated_cost: "5000" }] }),
    })
    openManualSearch(harness, "SBER")
    await findButton(harness.render(), "Рассчитать портфель").props.onClick()
    assert.ok(findCard(harness.render(), "SBER"))
    assert.ok(findButton(harness.render("account-7", () => {}), "Добавить выбранные инструменты"))
})

test("manual session uses explicit grid parameters and never calls rating filters", async () => {
    const requests = []
    const harness = createSelectionHarness(async () => ({ instruments: [] }), {
        previewInstrumentSelection: async () => { throw new Error("Old filters called") },
        previewGridSelection: async request => {
            requests.push(request)
            return { capital: request.capital, selections: [{ ...request.instruments[0], price: "100", estimated_cost: "500" }] }
        },
    })
    openManualSearch(harness, "SBER")
    let tree = harness.render()
    assert.doesNotMatch(textContent(tree), /Risk|Confidence|Разрешить высокий риск/)
    findElement(tree, item => item.props?.["aria-label"] === "Уровни актива 1").props.onChange({ target: { value: "5" } })
    findElement(harness.render(), item => item.props?.["aria-label"] === "Лотов в уровень актива 1").props.onChange({ target: { value: "2" } })
    await findButton(harness.render(), "Рассчитать портфель").props.onClick()
    assert.equal(requests[0].instruments[0].levels, 5)
    assert.equal(requests[0].instruments[0].quantity, 2)
    assert.equal(requests[0].trading_account_id, "account-7")
    assert.equal(findCard(harness.render(), "SBER").props.instrument.levels, 5)
})

test("selected LIVE account startup does not depend on legacy global flags", () => {
    const handler = source.slice(source.indexOf("async function startStrategy()"), source.indexOf("function openSession("))
    assert.doesNotMatch(handler, /liveTradingEnabled|LIVE_TRADING_ENABLED/)
    assert.match(handler, /!selectedTradingAccountId/)
    assert.match(handler, /!liveValidation\.success/)
    assert.match(handler, /await startLive\(/)
})

test("changing selection mode ignores an in-flight calculation response", async () => {
    let resolvePreview
    const harness = createSelectionHarness(async () => ({ instruments: [] }), {
        previewIndexSelection: () => new Promise(resolve => { resolvePreview = resolve }),
    })
    const pending = findButton(harness.render(), "Рассчитать индекс").props.onClick()
    findButton(harness.render(), "Авто").props.onClick()
    resolvePreview(gridPlan())
    await pending
    assert.equal(findCard(harness.render(), "SBER"), undefined)
})
