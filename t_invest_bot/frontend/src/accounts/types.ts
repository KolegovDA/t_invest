export type BrokerType =
    | "tinvest"
    | "alfa"
    | "bcs"
    | "finam"
    | "other"


export type TradingAccountMode =
    | "live"
    | "sandbox"


export type CommissionMode =
    | "auto"
    | "investor_030"
    | "trader_005"
    | "custom"


export interface BrokerCredentialField {
    key: string
    label: string
    type: string
    required: boolean
}


export interface BrokerInfo {
    id: BrokerType
    name: string
    supported: boolean

    credential_fields:
    BrokerCredentialField[]

    modes:
    TradingAccountMode[]
}


export interface TradingAccount {
    id: string

    name: string

    broker: BrokerType

    broker_account_id: string

    mode: TradingAccountMode

    credentials_configured: boolean

    commission_mode:
    CommissionMode

    custom_buy_commission_percent:
    string | null

    custom_sell_commission_percent:
    string | null

    detected_buy_commission_percent:
    string | null

    detected_sell_commission_percent:
    string | null

    expected_buy_commission_percent:
    string

    expected_sell_commission_percent:
    string

    enabled: boolean

    created_at: string | null

    updated_at: string | null
}


export interface BrokerPortfolio {
    cash: string

    total_value:
    string | null

    positions_count: number
}


export interface BrokerConnectionAccount {
    broker_account_id: string

    name: string

    status: string

    account_type: string
}


export interface BrokerConnectionResult {
    success: boolean

    broker: BrokerType

    broker_account_id:
    string | null

    account_found: boolean

    error:
    string | null

    accounts:
    BrokerConnectionAccount[]

    portfolio:
    BrokerPortfolio | null
}


export interface CreateTradingAccountPayload {
    name: string

    broker: BrokerType

    broker_account_id: string

    credentials:
    Record<string, string>

    mode:
    TradingAccountMode

    commission_mode:
    CommissionMode

    custom_buy_commission_percent?:
    string | null

    custom_sell_commission_percent?:
    string | null

    enabled: boolean
}


export interface UpdateTradingAccountPayload {
    name?: string

    broker?: BrokerType

    broker_account_id?: string

    credentials?:
    Record<string, string>

    mode?:
    TradingAccountMode

    commission_mode?:
    CommissionMode

    custom_buy_commission_percent?:
    string | null

    custom_sell_commission_percent?:
    string | null

    enabled?: boolean
}
