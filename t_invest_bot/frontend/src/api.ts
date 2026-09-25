import type {
    ActiveSession,
    ApiUsage,
    Dashboard,
    Instrument,
    InstrumentSearchResult,
    LiveStartValidationResult,
    LiveStatus,
    RunnerStatus,
    StartPlan,
    StartSandboxResult,
} from "./types"


const API_BASE_URL =
    window.location.origin


async function parseJsonResponse(
    response: Response
) {
    if (!response.ok) {
        const data =
            await response
                .json()
                .catch(
                    () => null
                )

        const message =
            data?.detail
            || `HTTP ${response.status}`

        throw new Error(
            typeof message
                === "string"
                ? message
                : JSON.stringify(
                    message
                )
        )
    }

    return response.json()
}


export async function getDashboard():
    Promise<Dashboard> {
    const response =
        await fetch(
            `${API_BASE_URL}/api/dashboard`
        )

    return parseJsonResponse(
        response
    )
}


export async function getApiUsage():
    Promise<ApiUsage> {
    const response =
        await fetch(
            `${API_BASE_URL}/api/api-usage`
        )

    return parseJsonResponse(
        response
    )
}


export async function getRunnerStatus():
    Promise<{
        runners: RunnerStatus[]
    }> {
    const response =
        await fetch(
            `${API_BASE_URL}/api/runner-status`
        )

    return parseJsonResponse(
        response
    )
}


export async function getInstruments():
    Promise<{
        instruments: Instrument[]
    }> {
    const response =
        await fetch(
            `${API_BASE_URL}/api/instruments`
        )

    return parseJsonResponse(
        response
    )
}


export async function searchInstruments(
    query: string,

    tradingAccountId?:
        string | null,

    limit: number = 30
): Promise<{
    instruments: InstrumentSearchResult[]
}> {
    const params =
        new URLSearchParams()

    params.set(
        "query",
        query
    )

    params.set(
        "limit",
        String(limit)
    )

    if (
        tradingAccountId
    ) {
        params.set(
            "trading_account_id",
            tradingAccountId
        )
    }

    const response =
        await fetch(
            `${API_BASE_URL}/api/instruments/search?${params.toString()}`
        )

    return parseJsonResponse(
        response
    )
}


export async function getSessions():
    Promise<{
        sessions: ActiveSession[]
    }> {
    const response =
        await fetch(
            `${API_BASE_URL}/api/sessions`
        )

    return parseJsonResponse(
        response
    )
}


export async function getSession(
    ticker: string
): Promise<ActiveSession> {
    const response =
        await fetch(
            `${API_BASE_URL}/api/session/${encodeURIComponent(ticker)}`
        )

    return parseJsonResponse(
        response
    )
}


export async function stopSession(
    ticker: string
) {
    const response =
        await fetch(
            `${API_BASE_URL}/api/stop-session/${encodeURIComponent(ticker)}`,
            {
                method:
                    "POST",
            }
        )

    return parseJsonResponse(
        response
    )
}


export async function drainSession(
    ticker: string
): Promise<{
    ticker: string
    status: string
    runners_affected: number
    message: string
}> {
    const response =
        await fetch(
            `${API_BASE_URL}/api/drain-session/${encodeURIComponent(ticker)}`,
            {
                method: "POST",
            }
        )

    return parseJsonResponse(
        response
    )
}


export async function calculateStartPlan(
    instruments: {
        ticker:
        string

        levels:
        number

        quantity:
        number
    }[],

    tradingAccountId?:
        string | null,

    sandboxAvailableCash:
        number | null = 100000
): Promise<StartPlan> {
    const response =
        await fetch(
            `${API_BASE_URL}/api/start-plan`,
            {
                method:
                    "POST",

                headers: {
                    "Content-Type":
                        "application/json",
                },

                body:
                    JSON.stringify({
                        available_cash:
                            tradingAccountId
                                ? null
                                : sandboxAvailableCash,

                        trading_account_id:
                            tradingAccountId
                            ?? null,

                        instruments,
                    }),
            }
        )

    return parseJsonResponse(
        response
    )
}


export async function validateLiveStart(
    tradingAccountId: string,

    instruments: {
        ticker:
        string

        levels:
        number

        quantity:
        number
    }[]
): Promise<LiveStartValidationResult> {
    const response =
        await fetch(
            `${API_BASE_URL}/api/start-live/validate`,
            {
                method:
                    "POST",

                headers: {
                    "Content-Type":
                        "application/json",
                },

                body:
                    JSON.stringify({
                        force:
                            false,

                        trading_account_id:
                            tradingAccountId,

                        instruments,
                    }),
            }
        )

    return parseJsonResponse(
        response
    )
}


export async function startSandbox(
    force: boolean,

    instruments: {
        ticker:
        string

        levels:
        number

        quantity:
        number
    }[],

    tradingAccountId?:
        string | null
): Promise<StartSandboxResult> {
    const response =
        await fetch(
            `${API_BASE_URL}/api/start-sandbox`,
            {
                method:
                    "POST",

                headers: {
                    "Content-Type":
                        "application/json",
                },

                body:
                    JSON.stringify({
                        force,

                        trading_account_id:
                            tradingAccountId
                            ?? null,

                        instruments,
                    }),
            }
        )

    return parseJsonResponse(
        response
    )
}


export async function getLiveStatus():
    Promise<LiveStatus> {
    const response =
        await fetch(
            `${API_BASE_URL}/api/live/status`
        )

    return parseJsonResponse(
        response
    )
}


export async function startLive(
    force: boolean,

    instruments: {
        ticker:
        string

        levels:
        number

        quantity:
        number
    }[],

    tradingAccountId?:
        string | null
): Promise<StartSandboxResult> {
    const response =
        await fetch(
            `${API_BASE_URL}/api/start-live`,
            {
                method:
                    "POST",

                headers: {
                    "Content-Type":
                        "application/json",
                },

                body:
                    JSON.stringify({
                        force,

                        trading_account_id:
                            tradingAccountId
                            ?? null,

                        instruments,
                    }),
            }
        )

    return parseJsonResponse(
        response
    )
}


export interface HealthResponse {
    status:
    string

    version?:
    string

    trading_mode:
    string

    live_trading_enabled:
    boolean

    real_sandbox_enabled:
    boolean

    state_persistence_enabled?:
    boolean

    multi_account_enabled?:
    boolean

    multi_broker_architecture?:
    boolean

    database_path?:
    string
}


export async function getHealth():
    Promise<HealthResponse> {
    const response =
        await fetch(
            `${API_BASE_URL}/api/health`
        )

    return parseJsonResponse(
        response
    )
}
