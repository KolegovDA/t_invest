import { useEffect, useState } from "react"
import { getHealth, getVersion } from "./api"

export default function App() {
    const [health, setHealth] = useState("")
    const [version, setVersion] = useState("")

    useEffect(() => {
        getHealth().then(data => {
            setHealth(data.status)
        })

        getVersion().then(data => {
            setVersion(data.version)
        })
    }, [])

    return (
        <div
            style={{
                padding: 20,
                maxWidth: 500,
                margin: "0 auto",
                fontFamily: "sans-serif"
            }}
        >
            <h1>T-Invest Bot</h1>

            <p>
                API: {health}
            </p>

            <p>
                Version: {version}
            </p>
        </div>
    )
}
