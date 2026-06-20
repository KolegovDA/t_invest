const API_HOST = window.location.hostname
const API_BASE_URL = `http://${API_HOST}:8000`

export async function getDashboard() {
    const response = await fetch(`${API_BASE_URL}/api/dashboard`)
    return response.json()
}

export async function getApiUsage() {
    const response = await fetch(`${API_BASE_URL}/api/api-usage`)
    return response.json()
}

export async function getInstruments() {
    const response = await fetch(`${API_BASE_URL}/api/instruments`)
    return response.json()
}

export async function getSessions() {
    const response = await fetch(`${API_BASE_URL}/api/sessions`)
    return response.json()
}

export async function getSession(ticker: string) {
    const response = await fetch(`${API_BASE_URL}/api/session/${ticker}`)
    return response.json()
}

export async function stopSession(ticker: string) {
    const response = await fetch(`${API_BASE_URL}/api/stop-session/${ticker}`, {
        method: "POST",
    })

    return response.json()
}

export async function calculateStartPlan(
    instruments: {
        ticker: string
        levels: number
        quantity: number
    }[]
) {
    const response = await fetch(`${API_BASE_URL}/api/start-plan`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            available_cash: 100000,
            instruments,
        }),
    })

    return response.json()
}

export async function startSandbox(
    force: boolean,
    instruments: {
        ticker: string
        levels: number
        quantity: number
    }[]
) {
    const response = await fetch(`${API_BASE_URL}/api/start-sandbox`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            force,
            instruments,
        }),
    })

    return response.json()
}
