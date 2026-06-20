export type Dashboard = {
    accounts: number
    capital: number
    active_positions: number
    profit: number
    instruments: string[]
}

export type Instrument = {
    ticker: string
    levels: number
    price: number
    required_capital: number
    quantity?: number
}

export type StartPlan = {
    available_cash: string
    total_required: string
    remaining_cash: string
    missing_cash: string
    can_start: boolean
    can_start_forced: boolean
    capital_utilization_percent: string
    instruments: {
        ticker: string
        levels: number
        quantity: number
        last_price: string
        required_deposit: string
    }[]
}

export type ActiveSession = {
    ticker: string
    levels: number
    quantity: number
    status: string
    positions: number
    current_price: number
    realized_profit: number
    unrealized_profit: number
    total_profit: number
}

export type ApiUsage = {
    total_weight: number
    events_count: number
    by_operation: Record<string, number>
}
