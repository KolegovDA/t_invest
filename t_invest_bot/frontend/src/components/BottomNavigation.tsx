export type AppTab =
    | "home"
    | "sessions"
    | "instruments"
    | "accounts"
    | "api"
    | "settings"


type Props = {
    activeTab: AppTab
    onChange: (tab: AppTab) => void
}


const items: {
    tab: AppTab
    icon: string
    label: string
}[] = [
        {
            tab: "home",
            icon: "⌂",
            label: "Главная",
        },
        {
            tab: "sessions",
            icon: "◉",
            label: "Сессии",
        },
        {
            tab: "instruments",
            icon: "≋",
            label: "Инструменты",
        },
        {
            tab: "accounts",
            icon: "▣",
            label: "Счета",
        },
        {
            tab: "api",
            icon: "↕",
            label: "API",
        },
        {
            tab: "settings",
            icon: "⚙",
            label: "Настройки",
        },
    ]


export function BottomNavigation({
    activeTab,
    onChange,
}: Props) {
    return (
        <div
            style={{
                position: "fixed",
                left: 0,
                right: 0,
                bottom: 0,
                zIndex: 500,

                background:
                    "rgba(255,255,255,0.96)",

                borderTop:
                    "1px solid #e5e7eb",

                backdropFilter:
                    "blur(14px)",
            }}
        >
            <div
                style={{
                    maxWidth: 560,
                    margin: "0 auto",

                    display: "grid",

                    gridTemplateColumns:
                        "repeat(6, 1fr)",

                    paddingBottom:
                        "env(safe-area-inset-bottom)",
                }}
            >
                {items.map(
                    item => {
                        const active =
                            item.tab ===
                            activeTab

                        return (
                            <button
                                key={
                                    item.tab
                                }

                                onClick={() =>
                                    onChange(
                                        item.tab
                                    )
                                }

                                style={{
                                    border:
                                        "none",

                                    background:
                                        "transparent",

                                    padding:
                                        "9px 2px 7px",

                                    color:
                                        active
                                            ? "#2563eb"
                                            : "#6b7280",

                                    cursor:
                                        "pointer",
                                }}
                            >
                                <div
                                    style={{
                                        fontSize:
                                            22,

                                        lineHeight:
                                            1,

                                        marginBottom:
                                            5,
                                    }}
                                >
                                    {
                                        item.icon
                                    }
                                </div>

                                <div
                                    style={{
                                        fontSize:
                                            9,

                                        fontWeight:
                                            active
                                                ? 700
                                                : 500,
                                    }}
                                >
                                    {
                                        item.label
                                    }
                                </div>
                            </button>
                        )
                    }
                )}
            </div>
        </div>
    )
}
