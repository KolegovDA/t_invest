import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import test from "node:test"
import { Script, createContext } from "node:vm"

const html = readFileSync(new URL("../head_server/static/index.html", import.meta.url), "utf8")
const script = html.match(/<script>([\s\S]*)<\/script>/)[1]
const settingsScript = script.slice(script.indexOf("async function loadTradingSettings()"), script.indexOf("async function saveAssetTradingSettings"))
const escapeScript = script.slice(script.indexOf("function esc(text)"), script.indexOf("async function login()"))

function settingsContext(byPlatform, byAsset, opened = []) {
    const box = { innerHTML: "", querySelectorAll: () => opened.map(id => ({ id })) }
    const error = { textContent: "" }
    const context = createContext({
        document: { getElementById: id => id === "tradingSettings" ? box : error },
        api: async path => path.endsWith("/asset-trading-settings") ? { by_asset: byAsset } : { by_platform: byPlatform },
    })
    new Script(escapeScript + settingsScript).runInContext(context)
    return { box, error, load: () => new Script("loadTradingSettings()").runInContext(context) }
}

test("head UI JavaScript parses without executing server or browser startup", () => {
    assert.doesNotThrow(() => new Script(script))
})

test("mobile overview keeps five compact tiles on one row", () => {
    assert.match(html, /@media \(max-width:600px\) \{\s*\.stat-grid \{ grid-template-columns:repeat\(5, minmax\(0, 1fr\)\); gap:4px; overflow:visible; \}/)
    assert.equal((html.match(/class="stat-tile"/g) || []).length, 5)
})

test("settings nest per-asset forms inside collapsible platform cards", async () => {
    const fixture = settingsContext({}, { bybit: { ETHUSDT: { take_profit_percent: "0.8" } } })
    await fixture.load()
    assert.equal(fixture.error.textContent, "")
    assert.match(fixture.box.innerHTML, /<details class="settings-user" id="trading-platform-tinvest"/)
    assert.match(fixture.box.innerHTML, /id="trading-platform-bybit-asset-ETHUSDT"/)
    assert.match(fixture.box.innerHTML, /name="take_profit_percent"[^>]*value="0.8"/)
    assert.match(fixture.box.innerHTML, /type="hidden" name="platform" value="bybit"/)
    assert.match(fixture.box.innerHTML, /Общие настройки/)
    assert.match(fixture.box.innerHTML, /Добавить актив/)
})

test("reloading settings retains opened platforms and assets and escapes values", async () => {
    const fixture = settingsContext({}, { future_broker: { 'A<script>': { trailing_percent: '" onfocus="bad' } } }, ["trading-platform-future_broker", "trading-platform-future_broker-asset-A<script>"])
    await fixture.load()
    assert.match(fixture.box.innerHTML, /id="trading-platform-future_broker" open/)
    assert.match(fixture.box.innerHTML, /id="trading-platform-future_broker-asset-A&lt;script&gt;" open/)
    assert.match(fixture.box.innerHTML, /value="&quot; onfocus=&quot;bad"/)
    assert.doesNotMatch(fixture.box.innerHTML, /<script>|value="" onfocus="bad/)
})

test("failed settings requests show an error without discarding existing forms", async () => {
    const fixture = settingsContext({}, {})
    fixture.box.innerHTML = "existing forms"
    const context = createContext({
        document: { getElementById: id => id === "tradingSettings" ? fixture.box : fixture.error },
        api: async () => { throw new Error("offline") },
    })
    new Script(escapeScript + settingsScript).runInContext(context)
    await new Script("loadTradingSettings()").runInContext(context)
    assert.equal(fixture.error.textContent, "offline")
    assert.equal(fixture.box.innerHTML, "existing forms")
})
