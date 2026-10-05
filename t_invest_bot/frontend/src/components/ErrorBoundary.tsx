import {
    Component,
} from "react"

import type {
    ErrorInfo,
    ReactNode,
} from "react"


type Props = {
    children: ReactNode
}


type State = {
    error: Error | null
}


export class ErrorBoundary extends Component<Props, State> {
    state: State = {
        error: null,
    }


    static getDerivedStateFromError(
        error: Error
    ): State {
        return {
            error,
        }
    }


    componentDidCatch(
        error: Error,
        info: ErrorInfo
    ) {
        console.error(
            "UI error:",

            error,

            info.componentStack,
        )
    }


    render() {
        if (
            this
            .state
            .error
        ) {
            return (
                <div
                    style={{
                        padding: 24,

                        color: "#b91c1c",

                        fontSize: 14,
                    }}
                >
                    <b>
                        Ошибка интерфейса
                    </b>

                    <pre
                        style={{
                            whiteSpace: "pre-wrap",

                            wordBreak: "break-word",
                        }}
                    >
                        {String(
                            this
                            .state
                            .error,
                        )}
                    </pre>

                    <button
                        onClick={() => {
                            this.setState(
                                {
                                    error: null,
                                }
                            )
                        }}
                    >
                        Повторить
                    </button>
                </div>
            )
        }

        return (
            this
            .props
            .children
        )
    }
}
