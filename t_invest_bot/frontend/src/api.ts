import type {
    AccountsOverview,
    ActiveSession,
    ApiUsage,
    CommissionSummary,
    Dashboard,
    DashboardHistory,
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


export async function getDashboardHistory(
    days: number
): Promise<DashboardHistory> {
    const response =
        await fetch(
            `${API_BASE_URL}/api/dashboard/history?days=${days}`
        )

    return parseJsonResponse(
        response
    )
}


export async function getCommissionSummary(
    limit: number = 50
): Promise<CommissionSummary> {
    const response =
        await fetch(
            `${API_BASE_URL}/api/commission/summary?limit=${limit}`
        )

    return parseJsonResponse(
        response
    )
}


export async function getOperations(
    limit?: number
): Promise<OperationsResponse> {
    const response =
        await fetch(
            `${API_BASE_URL}/api/operations${limit === undefined ? "" : `?limit=${limit}`}`
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


export async function previewGridSelection(request: {
    capital: string
    instruments: { ticker: string; levels: number; quantity: number }[]
    trading_account_id?: string | null
}): Promise<GridSelectionPlan> {
    const response = await fetch(`${API_BASE_URL}/api/instrument-selection/grids`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
    })
    return parseJsonResponse(response)
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
        base_order_amount?: number
    }[],

    tradingAccountId?:
        string | null,
    bybitAutomatic: boolean = false
): Promise<StartSandboxResult> {
    const response = await fetch(`${API_BASE_URL}/api/start-live`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({force, trading_account_id: tradingAccountId ?? null, instruments, bybit_automatic: bybitAutomatic}),
    })
    return parseJsonResponse(response)
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

    days: number = 60,

    interval: string = "1d"
): Promise<SessionChartResponse> {
    const response =
        await fetch(
            `${API_BASE_URL}/api/session/${encodeURIComponent(ticker)}/chart?days=${days}&interval=${encodeURIComponent(interval)}`
        )

    return parseJsonResponse(
        response
    )
}


export async function getAccountsOverview():
    Promise<AccountsOverview> {
    const response =
        await fetch(
            `${API_BASE_URL}/api/overview`
        )

    return parseJsonResponse(
        response
    )
}


export async function updateProfile(
    request: {
        full_name?: string

        phone?: string

        email?: string

        birth_date?: string
    }
): Promise<AuthUserResponse> {
    const response =
        await fetch(
            `${API_BASE_URL}/api/auth/profile`,
            {
                method:
                "PATCH",

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


export interface HeadSyncEntry {
    id: number

    created_at:
    string

    payload:
    Record<string, unknown>
}


export interface HeadHistoryResponse {
    available: boolean

    client?:
    Record<string, unknown>

    syncs:
    HeadSyncEntry[]
}


export async function getHeadHistory(
    limit: number = 20
): Promise<HeadHistoryResponse> {
    const response =
        await fetch(
            `${API_BASE_URL}/api/user/head-history?limit=${limit}`
        )

    return parseJsonResponse(
        response
    )
}


export interface TopupRequest {
    id: number

    created_at:
    string

    amount: string

    comment: string

    document_name?:
    string | null

    status:
    "pending"
    | "approved"
    | "rejected"

    review_note?:
    string | null

    reviewed_at?:
    string | null

    applied?: boolean
}


export interface TopupsResponse {
    available: boolean

    requests:
    TopupRequest[]

    balance: string
}


export interface TopupSubmitResponse {
    request:
    TopupRequest

    balance: string
}


export async function submitTopup(
    request: {
        amount: string

        comment: string

        document?:
        File | null
    }
): Promise<TopupSubmitResponse> {
    const form =
        new FormData()

    form.append(
        "amount",
        request.amount
    )

    form.append(
        "comment",
        request.comment
    )

    if (
        request.document
    ) {
        form.append(
            "document",
            request.document
        )
    }

    const response =
        await fetch(
            `${API_BASE_URL}/api/user/topup`,
            {
                method:
                "POST",

                body:
                form,
            }
        )

    return parseJsonResponse(
        response
    )
}


export async function getTopups(
    limit: number = 20
): Promise<TopupsResponse> {
    const response =
        await fetch(
            `${API_BASE_URL}/api/user/topups?limit=${limit}`
        )

    return parseJsonResponse(
        response
    )
}


export interface AuthUser {
    id: number

    login: string

    full_name: string

    phone?:
    string | null

    email?:
    string | null

    birth_date?:
    string | null
}

export interface AuthStatusResponse {
    auth_required: boolean

    has_users: boolean

    device_has_pin: boolean

    device_has_biometric: boolean
}

export interface AuthRegisterRequest {
    full_name: string

    phone: string

    email: string

    birth_date: string

    login: string

    password: string

    device_id: string
}

export interface AuthUserResponse {
    user: AuthUser
}

export interface AuthStatusOnlyResponse {
    status: string
}

async function postJson(
    url: string,

    body: unknown,
) {
    const response =
        await fetch(
            `${API_BASE_URL}${url}`,
            {
                method:
                "POST",

                headers: {
                    "Content-Type":
                    "application/json",
                },

                body:
                JSON.stringify(
                    body
                ),
            }
        )

    return parseJsonResponse(
        response
    )
}

export async function getAuthStatus(
    deviceId: string
): Promise<AuthStatusResponse> {
    const params =
        new URLSearchParams()

    params.set(
        "device_id",
        deviceId
    )

    const response =
        await fetch(
            `${API_BASE_URL}/api/auth/status?${params.toString()}`
        )

    return parseJsonResponse(
        response
    )
}

export async function getAuthMe():
    Promise<AuthUserResponse> {
    const response =
        await fetch(
            `${API_BASE_URL}/api/auth/me`
        )

    return parseJsonResponse(
        response
    )
}

export async function authRegister(
    request: AuthRegisterRequest
): Promise<AuthUserResponse> {
    return postJson(
        "/api/auth/register",
        request
    )
}

export async function authLogin(
    login: string,

    password: string,

    deviceId: string
): Promise<AuthUserResponse> {
    return postJson(
        "/api/auth/login",
        {
            login,

            password,

            device_id:
            deviceId,
        }
    )
}

export async function authPasswordReset(
    login: string,

    code: string,

    password: string,

    deviceId: string
): Promise<AuthUserResponse> {
    return postJson(
        "/api/auth/password/reset",
        {
            login,

            code,

            password,

            device_id:
            deviceId,
        }
    )
}

export async function authVerifyPin(
    deviceId: string,

    pin: string
): Promise<AuthUserResponse> {
    return postJson(
        "/api/auth/pin/verify",
        {
            device_id:
            deviceId,

            pin,
        }
    )
}

export async function authSetPin(
    deviceId: string,

    pin: string
): Promise<AuthStatusOnlyResponse> {
    return postJson(
        "/api/auth/pin/set",
        {
            device_id:
            deviceId,

            pin,
        }
    )
}

export async function authVerifyBiometric(
    deviceId: string,

    credentialId: string
): Promise<AuthUserResponse> {
    return postJson(
        "/api/auth/biometric/verify",
        {
            device_id:
            deviceId,

            credential_id:
            credentialId,
        }
    )
}

export async function authRegisterBiometric(
    deviceId: string,

    credentialId: string
): Promise<AuthStatusOnlyResponse> {
    return postJson(
        "/api/auth/biometric/register",
        {
            device_id:
            deviceId,

            credential_id:
            credentialId,
        }
    )
}

export async function authDisableBiometric(
    deviceId: string
): Promise<AuthStatusOnlyResponse> {
    return postJson(
        "/api/auth/biometric/disable",
        {
            device_id:
            deviceId,

            credential_id:
            "",
        }
    )
}

export async function authLogout():
    Promise<AuthStatusOnlyResponse> {
    return postJson(
        "/api/auth/logout",
        {}
    )
}


export interface PushVapidKeyResponse {
    public_key:
    string

    csrf_token: string
}


export async function getPushVapidKey():
    Promise<PushVapidKeyResponse> {
    const response =
        await fetch(
            `${API_BASE_URL}/api/push/vapid-key`
        )

    return parseJsonResponse(
        response
    )
}


export async function subscribeToPush(
    subscription: {
        endpoint:
        string

        keys:
        Record<string, string>
    }
): Promise<{ status: string }> {
    return pushRequest("/api/push/subscribe", "POST", subscription)
}


export async function unsubscribeFromPush(
    endpoint: string
): Promise<{ status: string }> {
    return pushRequest(`/api/push/subscribe?endpoint=${encodeURIComponent(endpoint)}`, "DELETE")
}


export async function sendTestPush(endpoint: string):
    Promise<{ status: string }> {
    return pushRequest("/api/push/test", "POST", { endpoint })
}

async function pushRequest(url: string, method: "POST" | "DELETE", body?: unknown): Promise<{ status: string }> {
    const { csrf_token } = await getPushVapidKey()
    const response = await fetch(`${API_BASE_URL}${url}`, {
        method,
        headers: { "Content-Type": "application/json", "X-ESM-CSRF": csrf_token },
        body: body === undefined ? undefined : JSON.stringify(body),
    })
    return parseJsonResponse(response)
}
