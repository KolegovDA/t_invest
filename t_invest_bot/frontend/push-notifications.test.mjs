import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { createRequire } from "node:module"
import test from "node:test"
import { runInNewContext } from "node:vm"
import ts from "typescript"

const require = createRequire(import.meta.url)
const source = readFileSync(new URL("./src/components/NotificationSettingsCard.tsx", import.meta.url), "utf8")
const compiled = ts.transpileModule(`${source}\nexport { pushRegistration }`, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2020 },
}).outputText

function registrationHarness(serviceWorker, secure = true) {
    const exports = {}
    const timers = new Map()
    runInNewContext(compiled, {
        exports, Error,
        require: name => name === "../api" ? {} : require(name),
        window: { isSecureContext: secure }, navigator: { serviceWorker },
        setTimeout: callback => { timers.set(callback, callback); return callback },
        clearTimeout: callback => timers.delete(callback),
    })
    return { run: exports.pushRegistration, expire: () => [...timers.values()].forEach(callback => callback()), timers }
}

test("push registration rejects insecure origins without starting registration", async () => {
    const harness = registrationHarness({ register: () => { throw new Error("Must not run") } }, false)
    await assert.rejects(harness.run(), /HTTPS/)
})

test("push registration explicitly registers the worker and clears its timeout", async () => {
    const calls = []
    const registration = { pushManager: {} }
    const harness = registrationHarness({ register: async path => calls.push(path), ready: Promise.resolve(registration) })
    assert.equal(await harness.run(), registration)
    assert.deepEqual(calls, ["/service-worker.js"])
    assert.equal(harness.timers.size, 0)
})

test("pending worker registration cannot wait indefinitely", async () => {
    const harness = registrationHarness({ register: () => new Promise(() => {}), ready: new Promise(() => {}) })
    const pending = harness.run()
    harness.expire()
    await assert.rejects(pending, /10 секунд/)
})

test("worker registration failures are propagated rather than silently ignored", async () => {
    const harness = registrationHarness({ register: async () => { throw new Error("worker unavailable") } })
    await assert.rejects(harness.run(), /worker unavailable/)
    assert.equal(harness.timers.size, 0)
})

test("test push targets this device and existing subscriptions are restored on the server", () => {
    assert.match(source, /sendTestPush\(subscription\.endpoint\)/)
    assert.match(source, /await subscribeToPush\(\{ endpoint: existing\.endpoint/)
    assert.match(source, /current\.byteLength !== expected\.length/)
    assert.match(source, /Подтверждением доставки/)
})

test("push mutations obtain session-bound CSRF tokens before sending requests", async () => {
    const apiSource = readFileSync(new URL("./src/api.ts", import.meta.url), "utf8")
    const apiCompiled = ts.transpileModule(apiSource, {
        compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
    }).outputText
    const exports = {}
    const calls = []
    runInNewContext(apiCompiled, {
        exports, URLSearchParams, Error,
        window: { location: { origin: "https://app.example" } },
        fetch: async (url, options) => {
            calls.push({ url, options })
            return { ok: true, json: async () => url.endsWith("vapid-key") ? { public_key: "key", csrf_token: "session-token" } : { status: "ok" } }
        },
    })
    await exports.subscribeToPush({ endpoint: "https://fcm.googleapis.com/device", keys: {} })
    await exports.unsubscribeFromPush("https://fcm.googleapis.com/device")
    await exports.sendTestPush("https://fcm.googleapis.com/device")
    assert.equal(calls.length, 6)
    for (let index = 0; index < calls.length; index += 2) {
        assert.match(calls[index].url, /\/api\/push\/vapid-key$/)
        assert.equal(calls[index + 1].options.headers["X-ESM-CSRF"], "session-token")
    }
    assert.deepEqual(calls.filter((_, index) => index % 2).map(call => call.options.method), ["POST", "DELETE", "POST"])
})

test("service worker shows a notification while the page is closed and opens its own origin", async () => {
    const handlers = {}
    const notifications = []
    const windows = []
    runInNewContext(readFileSync(new URL("./public/service-worker.js", import.meta.url), "utf8"), {
        self: {
            addEventListener: (name, callback) => { handlers[name] = callback },
            registration: { showNotification: async (title, options) => notifications.push({ title, options }) },
            clients: { matchAll: async () => [], openWindow: async path => windows.push(path) },
        },
    })
    let pending
    handlers.push({ data: { json: () => ({ title: "ESM Trade", body: "SELL Bybit ETHUSDT" }) }, waitUntil: promise => { pending = promise } })
    await pending
    assert.equal(notifications[0].options.body, "SELL Bybit ETHUSDT")
    let closed = false
    handlers.notificationclick({ notification: { close: () => { closed = true } }, waitUntil: promise => { pending = promise } })
    await pending
    assert.equal(closed, true)
    assert.deepEqual(windows, ["/"])
})
