const API_BASE_URL = window.location.origin


async function parseJsonResponse(response: Response) {
    if (!response.ok) {
        const text = await response.text()

        throw new Error(
            `API error ${response.status}: ${text}`
        )
    }

    return response.json()
}


export async function getDashboard() {
    const response = await fetch(
        `${API_BASE_URL}/api/dashboard`
    )

    return parseJsonResponse(response)
}


export async function getApiUsage() {
    const response = await fetch(
        `${API_BASE_URL}/api/api-usage`
    )

    return parseJsonResponse(response)
}


export async function getRunnerStatus() {
    const response = await fetch(
        `${API_BASE_URL}/api/runner-status`
    )

    return parseJsonResponse(response)
}


export async function getInstruments() {
    const response = await fetch(
        `${API_BASE_URL}/api/instruments`
    )

    return parseJsonResponse(response)
}


export async function getSessions() {
    const response = await fetch(
        `${API_BASE_URL}/api/sessions`
    )

    return parseJsonResponse(response)
}


export async function getSession(
    ticker: string
) {
    const response = await fetch(
        `${API_BASE_URL}/api/session/${encodeURIComponent(ticker)}`
    )

    return parseJsonResponse(response)
}


export async function stopSession(
    ticker: string
) {
    const response = await fetch(
        `${API_BASE_URL}/api/stop-session/${encodeURIComponent(ticker)}`,
        {
            method: "POST",
        }
    )

    return parseJsonResponse(response)
}


export async function calculateStartPlan(
    instruments: {
        ticker: string
        levels: number
        quantity: number
    }[]
) {
    const response = await fetch(
        `${API_BASE_URL}/api/start-plan`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                available_cash: 100000,
                instruments,
            }),
        }
    )

    return parseJsonResponse(response)
}


export async function startSandbox(
    force: boolean,
    instruments: {
        ticker: string
        levels: number
        quantity: number
    }[]
) {
    const response = await fetch(
        `${API_BASE_URL}/api/start-sandbox`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                force,
                instruments,
            }),
        }
    )

    return parseJsonResponse(response)
}


export async function startLive(
    force: boolean,
    instruments: {
        ticker: string
        levels: number
        quantity: number
    }[]
) {
    const response = await fetch(
        `${API_BASE_URL}/api/start-live`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                force,
                instruments,
            }),
        }
    )

    return parseJsonResponse(response)
}


export async function getLiveStatus() {
    const response = await fetch(
        `${API_BASE_URL}/api/live/status`
    )

    return parseJsonResponse(response)
}


export interface HealthResponse {
    status: string
    trading_mode: string
    live_trading_enabled: boolean
    real_sandbox_enabled: boolean
}


export async function getHealth(): Promise<HealthResponse> {
    const response = await fetch(
        `${API_BASE_URL}/api/health`
    )

    return parseJsonResponse(response)
}
