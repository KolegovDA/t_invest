import { useState } from "react"

import {
    getStoredTheme,
    setTheme,
    type Theme,
} from "../theme"


export function ThemeToggle() {
    const [
        theme,
        setThemeState,
    ] = useState<Theme>(
        () => (
            getStoredTheme()
        )
    )

    return (
        <button
            onClick={() => {
                const next: Theme = (
                    theme
                    === "dark"
                        ? "light"
                        : "dark"
                )

                setTheme(
                    next
                )

                setThemeState(
                    next
                )
            }}

            title={
                theme
                === "dark"
                    ? "Светлая тема"
                    : "Тёмная тема"
            }

            style={{
                border:
                "1px solid var(--border)",

                background:
                "var(--card-soft)",

                borderRadius:
                10,

                padding:
                "6px 12px",

                fontSize:
                16,

                cursor:
                "pointer",

                color:
                "var(--text)",
            }}
        >
            {
                theme
                === "dark"
                    ? "☾"
                    : "☀"
            }
        </button>
    )
}
