export type Theme = "dark" | "light"

export type PlatformColors = Record<"tinvest" | "bybit", string>

export const defaultPlatformColors: PlatformColors = {
    tinvest: "#f59e0b",
    bybit: "#22c55e",
}

export function getStoredPlatformColors(): PlatformColors {
    try {
        const stored = JSON.parse(localStorage.getItem("esm-platform-colors") ?? "{}")
        return {
            tinvest: /^#[0-9a-f]{6}$/i.test(stored?.tinvest) ? stored.tinvest : defaultPlatformColors.tinvest,
            bybit: /^#[0-9a-f]{6}$/i.test(stored?.bybit) ? stored.bybit : defaultPlatformColors.bybit,
        }
    } catch {
        return { ...defaultPlatformColors }
    }
}

export function storePlatformColors(colors: PlatformColors) {
    const validated = Object.fromEntries(Object.entries(defaultPlatformColors).map(([platform, fallback]) => [
        platform, /^#[0-9a-f]{6}$/i.test(colors[platform as keyof PlatformColors]) ? colors[platform as keyof PlatformColors] : fallback,
    ]))
    localStorage.setItem("esm-platform-colors", JSON.stringify(validated))
    window.dispatchEvent(new Event("esm-platform-colors-changed"))
}


const storageKey = "esm-theme"


export function getStoredTheme(): Theme {
    try {
        const stored = localStorage.getItem(
            storageKey
        )

        if (
            stored
            === "dark"
            || stored
            === "light"
        ) {
            return stored
        }
    } catch (error) {
    }

    return "dark"
}


export function applyTheme(
    theme: Theme
) {
    document.documentElement.setAttribute(
        "data-theme",
        theme
    )
}


export function storeTheme(
    theme: Theme
) {
    try {
        localStorage.setItem(
            storageKey,
            theme
        )
    } catch (error) {
    }
}


export function setTheme(
    theme: Theme
) {
    applyTheme(
        theme
    )

    storeTheme(
        theme
    )
}
