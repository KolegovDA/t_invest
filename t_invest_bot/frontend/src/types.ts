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

    broker:
    BrokerType

    broker_account_id:
    string

    mode:
    TradingAccountMode

    credentials_configured:
    boolean

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

    enabled:
    boolean

    created_at:
    string | null

    updated_at:
    string | null
}


export interface BrokerPortfolio {
    cash: string

    total_value:
    string | null

    positions_count:
    number
}


export interface BrokerConnectionAccount {
    broker_account_id:
    string

    name:
    string

    status:
    string

    account_type:
    string
}


export interface BrokerConnectionResult {
    success:
    boolean

    broker:
    BrokerType

    broker_account_id:
    string | null

    account_found:
    boolean

    error:
    string | null

    accounts:
    BrokerConnectionAccount[]

    portfolio:
    BrokerPortfolio | null
}


export interface CreateTradingAccountPayload {
    name:
    string

    broker:
    BrokerType

    broker_account_id:
    string

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

    enabled:
    boolean
}


export interface UpdateTradingAccountPayload {
    name?:
    string

    broker?:
    BrokerType

    broker_account_id?:
    string

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

    enabled?:
    boolean
}


export type Dashboard = {
    accounts:
    number

    active_accounts?:
    number

    capital:
    number | null

    available_cash?:
    number | null

    reserved_cash?:
    number | null

    active_positions:
    number

    profit:
    number

    instruments:
    string[]
}


export type ApiUsage = {
    total_weight:
    number

    events_count:
    number

    by_operation:
    Record<string, number>

    last_1s_weight:
    number

    last_60s_weight:
    number

    last_300s_weight:
    number

    active_sessions_count:
    number

    per_minute_per_session:
    number

    forecast_5_sessions_per_minute:
    number

    forecast_10_sessions_per_minute:
    number

    forecast_20_sessions_per_minute:
    number
}


export type RunnerStatus = {
    session_id?:
    string | null

    trading_account_id?:
    string | null

    is_running:
    boolean

    last_tick_at:
    string | null

    last_error:
    string | null

    ticks_count:
    number

    prices_checked_total:
    number

    orders_placed_total:
    number

    executions_total:
    number
}


export type Instrument = {
    ticker:
    string

    levels:
    number

    quantity:
    number

    price:
    number

    required_capital:
    number
}


export type ActiveSession = {
    ticker:
    string

    levels:
    number

    quantity:
    number

    status:
    string

    positions:
    number

    current_price:
    number

    realized_profit:
    number

    unrealized_profit:
    number

    total_profit:
    number
}


export type StartPlanInstrument = {
    ticker:
    string

    levels:
    number

    quantity:
    number

    last_price:
    string

    required_deposit:
    string
}


export type StartPlan = {
    available_cash:
    string

    total_required:
    string

    remaining_cash:
    string

    missing_cash:
    string

    can_start:
    boolean

    can_start_forced:
    boolean

    capital_utilization_percent:
    string

    instruments:
    StartPlanInstrument[]
}


export type StartSandboxResult = {
    status:
    string

    mode:
    string

    force:
    boolean

    real_sandbox_status?:
    string

    execution_status?:
    string

    account_id?:
    string | null

    trading_account_id?:
    string | null

    runner_session_id?:
    string | null

    sessions:
    ActiveSession[]
}


export type LiveStartValidationInstrument = {
    ticker:
    string

    instrument_uid:
    string

    current_price:
    string

    min_grid_price:
    string

    grid_step:
    string

    levels_count:
    number

    quantity:
    number
}


export type LiveStartValidationResult = {
    success:
    boolean

    trading_account_id:
    string

    broker:
    string

    broker_account_id:
    string

    account_name:
    string

    available_cash:
    string

    total_required_deposit:
    string

    remaining_cash:
    string

    missing_cash:
    string

    can_start:
    boolean

    can_start_forced:
    boolean

    capital_utilization_percent:
    string

    buy_commission_percent:
    string

    sell_commission_percent:
    string

    instruments:
    LiveStartValidationInstrument[]
}


export type LiveStatusAccount = {
    account_id:
    string

    name:
    string

    status:
    string

    account_type:
    string

    selected:
    boolean
}


export type LiveStatusPortfolio = {
    total_amount_shares:
    string

    total_amount_bonds:
    string

    total_amount_etf:
    string

    total_amount_currencies:
    string

    expected_yield:
    string

    positions_count:
    number
}


export type LiveStatus = {
    token_configured:
    boolean

    selected_account_id:
    string | null

    account_found:
    boolean

    live_trading_enabled:
    boolean

    trading_mode:
    string

    accounts:
    LiveStatusAccount[]

    portfolio:
    LiveStatusPortfolio | null

    unary_limits_count:
    number | null

    stream_limits_count:
    number | null

    error:
    string | null
}
