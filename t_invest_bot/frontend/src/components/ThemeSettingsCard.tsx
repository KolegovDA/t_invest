import {
    useState,
} from "react"

import {
    Theme,
    getStoredTheme,
    setTheme,
    defaultPlatformColors,
    getStoredPlatformColors,
    storePlatformColors,
} from "../theme"


const themes: Theme[] = [
    "dark",
    "light",
]


const themeLabels: Record<
    Theme,
    string
> = {
    dark: "Тёмная",

    light: "Светлая",
}


export function ThemeSettingsCard() {
    const [platformColors, setPlatformColors] = useState(getStoredPlatformColors)
    const [colorError, setColorError] = useState<string | null>(null)

    function saveColors(next: typeof platformColors) {
        try {
            storePlatformColors(next)
            setPlatformColors(next)
            setColorError(null)
        } catch {
            setColorError("Не удалось сохранить цвета в этом браузере.")
        }
    }

    const [
        theme,
        setLocalTheme,
    ] = useState<Theme>(
        getStoredTheme()
    )


    function selectTheme(
        next: Theme
    ) {
        setTheme(
            next
        )

        setLocalTheme(
            next
        )
    }


    return (
        <div
            style={{
                background:
                "var(--card)",

                borderRadius:
                14,

                padding:
                13,

                marginTop:
                10,

                color:
                "var(--text)",
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
                Оформление
            </h3>

            <div
                style={{
                    color:
                    "var(--text-muted)",

                    fontSize:
                    13,

                    marginBottom:
                    10,
                }}
            >
                Тема интерфейса: тёмная
                (Bybit-стиль) или светлая.
            </div>

            <div
                style={{
                    display:
                    "flex",

                    gap:
                    4,

                    padding:
                    4,

                    borderRadius:
                    10,

                    background:
                    "var(--card-soft)",
                }}
            >
                {themes.map(
                    (
                        item
                    ) => (
                        <button
                            key={
                                item
                            }

                            onClick={() => {
                                selectTheme(
                                    item
                                )
                            }}

                            style={{
                                flex:
                                1,

                                padding:
                                "8px 14px",

                                borderRadius:
                                8,

                                border:
                                theme
                                === item
                                    ? "1px solid var(--accent)"
                                    : "1px solid transparent",

                                background:
                                theme
                                === item
                                    ? "var(--accent-soft)"
                                    : "transparent",

                                color:
                                theme
                                === item
                                    ? "var(--accent)"
                                    : "var(--text-muted)",

                                fontWeight:
                                theme
                                === item
                                    ? 600
                                    : 400,

                                cursor:
                                theme
                                === item
                                    ? "default"
                                    : "pointer",
                            }}
                        >
                            {
                                themeLabels[
                                    item
                                ]
                            }
                        </button>
                    )
                )}
            </div>
            <div style={{ marginTop: 14, display: "flex", flexWrap: "wrap", gap: 12, alignItems: "center" }}>
                {(["tinvest", "bybit"] as const).map(platform => (
                    <label key={platform} style={{ display: "flex", gap: 8, alignItems: "center" }}>
                        {platform === "tinvest" ? "Т-Инвест" : "Bybit"}
                        <input type="color" aria-label={`Цвет графика ${platform === "tinvest" ? "Т-Инвест" : "Bybit"}`} value={platformColors[platform]}
                            onChange={event => saveColors({ ...platformColors, [platform]: event.target.value })} />
                    </label>
                ))}
                <button type="button" onClick={() => saveColors({ ...defaultPlatformColors })}>Сбросить цвета</button>
            </div>
            <div style={{ marginTop: 8, fontSize: 12, color: "var(--text-muted)" }}>Цвета графиков сохраняются в этом браузере. Общий баланс остаётся жёлтым.</div>
            {colorError && <div role="alert">{colorError}</div>}
        </div>
    )
}
