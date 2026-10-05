export type BrokerType =
    | "tinvest"
    | "bybit"
    | "alfa"
    | "bcs"
    | "finam"
    | "other"


export interface ReconciliationEvent {
    created_at:
    string

    trading_account_id:
    string | null

    instrument_id:
    string | null

    event_type:
    string

    details:
    string
}


export interface ReconciliationEventsResponse {
    events:
    ReconciliationEvent[]

    counts_by_type:
    Record<string, number>
}


export interface InstrumentSelectionItem {
    ticker:
    string

    instrument_uid:
    string

    name:
    string

    weight_percent:
    string

    allocated_capital:
    string

    confidence_value:
    string | null

    risk_band:
    string | null
}


export interface InstrumentSelectionPreview {
    capital:
    string

    selections:
    InstrumentSelectionItem[]

    rejected: {
        ticker:
        string

        reason:
        string
    }[]
}


export interface GridSelectionItem {
    ticker:
    string

    instrument_uid:
    string

    name:
    string

    currency:
    string

    price:
    string

    lot_size:
    number

    quantity:
    number

    levels:
    number

    volatility_percent:
    string

    risk_band:
    string

    estimated_cost:
    string

    allocated_capital:
    string
}


export interface GridSelectionPlan {
    mode:
    string

    index_id:
    string | null

    capital:
    string

    selections:
    GridSelectionItem[]

    rejected: {
        ticker:
        string

        reason:
        string
    }[]

    spent_capital:
    string

    remaining_capital:
    string
}


export interface IndexPresetInfo {
    index_id:
    string

    name:
    string

    description:
    string

    tickers_count:
    number

    tickers:
    string[]
}


export interface SelectionOptions {
    indexes:
    IndexPresetInfo[]

    auto: {
        universe_tickers_count:
        number
    }

    defaults: {
        desired_levels:
        number

        min_levels:
        number

        max_instruments:
        number

        quantity:
        number
    }
}


export interface KnowledgeInstrument {
    instrument_id:
    string

    total_cycles:
    number

    profitable_cycles:
    number

    losing_cycles:
    number

    total_profit:
    string

    max_drawdown:
    string

    average_cycle_profit:
    string

    compensation_closes:
    number

    total_trades:
    number
}


export interface KnowledgeInstrumentsResponse {
    instruments:
    KnowledgeInstrument[]
}


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


export type DashboardAccountDetail = {
    id:
    string

    name:
    string

    broker:
    string

    mode:
    string

    enabled:
    boolean

    currency:
    string

    balance:
    number | null

    pnl_today:
    number | null
}


export type Dashboard = {
    total_balance?: number | null
    total_balance_currency?: string
    balance_conversion_note?: string | null
    exchange_rates_rub?: Record<string, number>
    accounts:
    number

    active_accounts?:
    number

    capital:
    number | null

    total_equity?:
    number | null

    available_cash?:
    number | null

    available_cash_by_currency?:
    Record<string, number>

    reserved_cash?:
    number | null

    invested_cash?:
    number | null

    invested_cash_by_currency?:
    Record<string, number>

    accounts_detail?:
    DashboardAccountDetail[]

    active_positions:
    number

    realized_profit?:
    number

    unrealized_profit?:
    number

    profit:
    number

    instruments:
    string[]
}


export type EquityPoint = {
    ts: string

    equity: number
}


export type HistoryAccount = {
    broker?: string
    id:
    string

    name:
    string

    currency:
    string
}


export type DashboardHistory = {
    total_points?: EquityPoint[]
    total_balance_currency?: string
    exchange_rates_rub?: Record<string, number>
    history_note?: string

    days: number

    equity: number | null

    equity_by_currency?:
    Record<string, number>

    points: EquityPoint[]

    points_by_currency?:
    Record<string, EquityPoint[]>

    points_by_account?:
    Record<string, EquityPoint[]>

    accounts?:
    HistoryAccount[]

    pnl_today: number | null

    pnl_today_percent: number | null

    pnl_total?: number | null

    pnl_total_percent?: number | null

    updated_at: string
}


export type OverviewAsset = {
    ticker:
    string

    kind:
    string

    quantity:
    number | null

    quantity_precision:
    number

    price:
    number | null

    value:
    number | null

    change_24h:
    number | null

    change_24h_percent:
    number | null
}


export type OverviewOrderBought = {
    level_index:
    number

    price:
    string

    quantity:
    number

    exit_target:
    string | null
}


export type OverviewOrderPlanned = {
    level_index:
    number

    price:
    string

    status:
    string
}


export type OverviewSessionBlock = {
    closed_orders: number
    cycle_profit: number
    pnl_percent: number | null
    next_buy_activation: number | null
    next_sell_activation: number | null

    ticker:
    string

    status:
    string

    quantity:
    number | null

    positions:
    number

    current_price:
    number | null

    realized_profit:
    number | null

    unrealized_profit:
    number | null

    total_profit:
    number | null

    orders_bought:
    OverviewOrderBought[]

    orders_planned:
    OverviewOrderPlanned[]
}


export type OverviewAccount = {
    id:
    string

    name:
    string

    broker:
    string

    mode:
    string

    enabled:
    boolean

    currency:
    string

    equity:
    number | null

    available:
    number | null

    invested:
    number

    reserved:
    number | null

    balance_series:
    EquityPoint[]

    assets:
    OverviewAsset[]

    sessions:
    OverviewSessionBlock[]
}


export type AccountsOverview = {
    accounts:
    OverviewAccount[]
}


export type CommissionCharge = {
    id: number

    created_at: string

    trading_account_id:
    string | null

    broker: string

    instrument_id:
    string | null

    ticker:
    string | null

    level_index:
    number | null

    trade_profit: string

    percent: string

    amount: string

    balance_after: string
}


export type CommissionSummary = {
    balance: string

    forced_drain: boolean

    default_percent: string

    by_platform:
    Record<
        string,
        string
    >

    charges:
    CommissionCharge[]
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

    lifecycle_status?:
    string

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


export type InstrumentSearchResult = {
    instrument_uid:
    string

    ticker:
    string

    name:
    string

    currency:
    string

    lot_size:
    number

    min_price_step:
    string
}


export type ActiveSession = {
    ticker:
    string

    trading_account_id?:
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


export type OperationLogEntry = {
    broker?: string | null

    created_at:
    string

    trading_account_id:
    string | null

    instrument_id:
    string | null

    ticker:
    string | null

    event_type:
    string

    details:
    string
}


export type OperationsResponse = {
    operations:
    OperationLogEntry[]
}


export type PhantomEntry = {
    session_id:
    string

    trading_account_id:
    string

    broker_account_id:
    string

    mode:
    string

    status:
    string

    ticker:
    string

    instrument_uid:
    string

    open_positions:
    number

    open_lots:
    number

    active_orders:
    number

    broker_lots:
    number
}


export type PhantomsResponse = {
    phantoms:
    PhantomEntry[]

    errors:
    string[]

    checked_accounts:
    string[]
}


export type PhantomResolveItemRequest = {
    session_id:
    string

    instrument_uids:
    string[]
}


export type PhantomResolveResponse = {
    resolved: {
        session_id:
        string

        removed_instruments:
        number

        snapshot_deleted:
        boolean
    }[]
}


export type ChartCandle = {
    time:
    string

    open:
    string

    high:
    string

    low:
    string

    close:
    string
}


export type ChartLevel = {
    level_index:
    number

    price:
    string

    status:
    string
}


export type ChartPosition = {
    level_index:
    number

    entry_price:
    string

    quantity:
    number

    trailing_exit_target_price:
    string | null

    trailing_exit_highest_price:
    string | null
}


export type ChartTrade = {
    time:
    string

    side:
    string

    price:
    string
}


export type SessionChartResponse = {
    started_at?: string | null

    ticker:
    string

    interval:
    string

    session_id:
    string | null

    candles:
    ChartCandle[]

    levels:
    ChartLevel[]

    positions:
    ChartPosition[]

    trades:
    ChartTrade[]
}
