import type { ReactNode } from "react"

type Props = {
    title: string
    children: ReactNode
    onClose: () => void
}

export function AppModal({
    title,
    children,
    onClose,
}: Props) {
    return (
        <div
            style={{
                position: "fixed",
                inset: 0,
                zIndex: 1000,
                background: "rgba(15, 23, 42, 0.42)",
                display: "flex",
                alignItems: "flex-end",
                justifyContent: "center",
            }}
            onClick={onClose}
        >
            <div
                style={{
                    width: "100%",
                    maxWidth: 560,
                    maxHeight: "92vh",
                    overflowY: "auto",
                    background: "#f4f6f8",
                    borderRadius: "24px 24px 0 0",
                    padding: 16,
                    boxSizing: "border-box",
                }}
                onClick={event => event.stopPropagation()}
            >
                <div
                    style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        marginBottom: 16,
                    }}
                >
                    <h2
                        style={{
                            margin: 0,
                            fontSize: 22,
                        }}
                    >
                        {title}
                    </h2>

                    <button
                        onClick={onClose}
                        style={{
                            width: 38,
                            height: 38,
                            borderRadius: 19,
                            border: "none",
                            background: "#e5e7eb",
                            fontSize: 22,
                            cursor: "pointer",
                        }}
                    >
                        ×
                    </button>
                </div>

                {children}
            </div>
        </div>
    )
}
