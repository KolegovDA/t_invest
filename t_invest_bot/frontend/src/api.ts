import type {
    ActiveSession,
    ApiUsage,
    Dashboard,
    GridSelectionPlan,
    Instrument,
    InstrumentSearchResult,
    InstrumentSelectionPreview,
    KnowledgeInstrumentsResponse,
    LiveStartValidationResult,
    LiveStatus,
    OperationsResponse,
    PhantomsResponse,
    PhantomResolveItemRequest,
    PhantomResolveResponse,
    ReconciliationEventsResponse,
    RunnerStatus,
    SelectionOptions,
    SessionChartResponse,
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


export async function getOperations(
    limit: number = 100
): Promise<OperationsResponse> {
    const response =
        await fetch(
            `${API_BASE_URL}/api/operations?limit=${limit}`
        )

    return parseJsonResponse(
        response
    )
}


export async function getSelectionOptions():
    Promise<SelectionOptions> {
    const response =
        await fetch(
            `${API_BASE_URL}/api/instrument-selection/options`
        )

    return parseJsonResponse(
        response
    )
}


export async function previewIndexSelection(
    request: {
        index_id:
        string

        capital:
        string

        quantity:
        number

        trading_account_id?:
        string | null
    }
): Promise<GridSelectionPlan> {
    const response =
        await fetch(
            `${API_BASE_URL}/api/instrument-selection/index`,
            {
                method:
                "POST",

                headers: {
                    "Content-Type":
                    "application/json",
                },

                body:
                JSON.stringify(
                    request
                ),
            }
        )

    return parseJsonResponse(
        response
    )
}


export async function previewAutoSelection(
    request: {
        capital:
        string

        quantity:
        number

        max_price?:
        string | null

        max_instruments:
        number

        desired_levels?:
        number

        min_levels?:
        number

        trading_account_id?:
        string | null
    }
): Promise<GridSelectionPlan> {
    const response =
        await fetch(
            `${API_BASE_URL}/api/instrument-selection/auto`,
            {
                method:
                "POST",

                headers: {
                    "Content-Type":
                    "application/json",
                },

                body:
                JSON.stringify(
                    request
                ),
            }
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


export async function getReconciliationEvents(
    limit: number = 50
): Promise<ReconciliationEventsResponse> {
    const response =
        await fetch(
            `${API_BASE_URL}/api/reconciliation/events?limit=${limit}`
        )

    return parseJsonResponse(
        response
    )
}


export async function previewInstrumentSelection(
    request: {
        capital:
        string

        max_instruments:
        number

        min_confidence:
        string

        allow_high_risk:
        boolean

        candidates: {
            ticker:
            string

            risk_value:
            string

            confidence_value:
            string
        }[]
    }
): Promise<InstrumentSelectionPreview> {
    const response =
        await fetch(
            `${API_BASE_URL}/api/instrument-selection/preview`,
            {
                method:
                "POST",

                headers: {
                    "Content-Type":
                    "application/json",
                },

                body:
                JSON.stringify(
                    request
                ),
            }
        )

    return parseJsonResponse(
        response
    )
}


export async function getKnowledgeInstruments():
    Promise<KnowledgeInstrumentsResponse> {
    const response =
        await fetch(
            `${API_BASE_URL}/api/knowledge/instruments`
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
                method:
                "POST",
            }
        )

    return parseJsonResponse(
        response
    )
}


export async function resumeSession(
    ticker: string
): Promise<{
    ticker: string
    status: string
    runners_affected: number
    message: string
}> {
    const response =
        await fetch(
            `${API_BASE_URL}/api/resume-session/${encodeURIComponent(ticker)}`,
            {
                method:
                "POST",
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


export async function getPhantoms():
    Promise<PhantomsResponse> {
    const response =
        await fetch(
            `${API_BASE_URL}/api/phantoms`
        )

    return parseJsonResponse(
        response
    )
}


export async function resolvePhantoms(
    items: PhantomResolveItemRequest[]
): Promise<PhantomResolveResponse> {
    const response =
        await fetch(
            `${API_BASE_URL}/api/phantoms/resolve`,
            {
                method:
                    "POST",

                headers: {
                    "Content-Type":
                        "application/json",
                },

                body:
                    JSON.stringify({
                        items,
                    }),
            }
        )

    return parseJsonResponse(
        response
    )
}


export async function getSessionChart(
    ticker: string,

    days: number = 60
): Promise<SessionChartResponse> {
    const response =
        await fetch(
            `${API_BASE_URL}/api/session/${encodeURIComponent(ticker)}/chart?days=${days}`
        )

    return parseJsonResponse(
        response
    )
}
