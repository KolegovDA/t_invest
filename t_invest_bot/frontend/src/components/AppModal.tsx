import { useEffect, type ReactNode } from "react"

let openModals = 0
let restorePageScroll: (() => void) | null = null

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
    useEffect(() => {
        if (openModals === 0) {
            const body = document.body
            const html = document.documentElement
            const scrollY = window.scrollY
            const bodyStyles = {
                position: body.style.position,
                top: body.style.top,
                width: body.style.width,
                overflow: body.style.overflow,
            }
            const htmlOverflow = html.style.overflow
            body.style.position = "fixed"
            body.style.top = `-${scrollY}px`
            body.style.width = "100%"
            body.style.overflow = "hidden"
            html.style.overflow = "hidden"
            restorePageScroll = () => {
                Object.assign(body.style, bodyStyles)
                html.style.overflow = htmlOverflow
                window.scrollTo(0, scrollY)
            }
        }
        openModals += 1
        return () => {
            openModals -= 1
            if (openModals === 0) {
                restorePageScroll?.()
                restorePageScroll = null
            }
        }
    }, [])

    return (
        <div
            style={{
                position: "fixed",
                inset: 0,
                zIndex: 1000,
                background: "var(--overlay)",
                display: "flex",
                alignItems: "flex-end",
                justifyContent: "center",
                overscrollBehavior: "none",
            }}
            onClick={onClose}
        >
            <div
                style={{
                    width: "100%",
                    maxWidth: 560,
                    maxHeight: "92vh",
                    overflowY: "auto",
                    overscrollBehavior: "contain",
                    touchAction: "pan-y",
                    background: "var(--bg-soft)",
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
                            background: "var(--card-soft)",
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
