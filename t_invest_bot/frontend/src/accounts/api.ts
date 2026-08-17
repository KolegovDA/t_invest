import type {
    BrokerConnectionResult,
    BrokerInfo,
    BrokerPortfolio,
    CreateTradingAccountPayload,
    TradingAccount,
    UpdateTradingAccountPayload,
} from "./types"


const API_BASE_URL =
    window.location.origin


async function parseJsonResponse(
    response: Response
) {
    if (!response.ok) {
        const data = await response
            .json()
            .catch(() => null)

        const message =
            data?.detail
            || `HTTP ${response.status}`

        throw new Error(
            typeof message === "string"
                ? message
                : JSON.stringify(message)
        )
    }

    return response.json()
}


export async function getBrokers():
    Promise<BrokerInfo[]> {
    const response = await fetch(
        `${API_BASE_URL}/api/brokers`
    )

    const data =
        await parseJsonResponse(
            response
        )

    return data.brokers
}


export async function getTradingAccounts():
    Promise<TradingAccount[]> {
    const response = await fetch(
        `${API_BASE_URL}/api/accounts`
    )

    const data =
        await parseJsonResponse(
            response
        )

    return data.accounts
}


export async function getTradingAccount(
    accountId: string
): Promise<TradingAccount> {
    const response = await fetch(
        `${API_BASE_URL}/api/accounts/${encodeURIComponent(accountId)}`
    )

    return parseJsonResponse(
        response
    )
}


export async function createTradingAccount(
    payload:
        CreateTradingAccountPayload
): Promise<TradingAccount> {
    const response = await fetch(
        `${API_BASE_URL}/api/accounts`,
        {
            method: "POST",

            headers: {
                "Content-Type":
                    "application/json",
            },

            body: JSON.stringify(
                payload
            ),
        }
    )

    return parseJsonResponse(
        response
    )
}


export async function updateTradingAccount(
    accountId: string,

    payload:
        UpdateTradingAccountPayload
): Promise<TradingAccount> {
    const response = await fetch(
        `${API_BASE_URL}/api/accounts/${encodeURIComponent(accountId)}`,
        {
            method: "PUT",

            headers: {
                "Content-Type":
                    "application/json",
            },

            body: JSON.stringify(
                payload
            ),
        }
    )

    return parseJsonResponse(
        response
    )
}


export async function deleteTradingAccount(
    accountId: string
): Promise<void> {
    const response = await fetch(
        `${API_BASE_URL}/api/accounts/${encodeURIComponent(accountId)}`,
        {
            method: "DELETE",
        }
    )

    await parseJsonResponse(
        response
    )
}


export async function testTradingAccount(
    accountId: string
): Promise<BrokerConnectionResult> {
    const response = await fetch(
        `${API_BASE_URL}/api/accounts/${encodeURIComponent(accountId)}/test`,
        {
            method: "POST",
        }
    )

    return parseJsonResponse(
        response
    )
}


export async function getTradingAccountPortfolio(
    accountId: string
): Promise<BrokerPortfolio> {
    const response = await fetch(
        `${API_BASE_URL}/api/accounts/${encodeURIComponent(accountId)}/portfolio`
    )

    return parseJsonResponse(
        response
    )
}
