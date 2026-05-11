export interface StockInfo {
  stock_code: string
  stock_name: string
  is_active: boolean
  current_price: number | null
  change_percent: number | null
}

export interface PricePoint {
  price: number
  open: number
  high: number
  low: number
  prev_close: number
  volume: number
  change: number
  change_percent: number
  timestamp: string
}

export interface Decision {
  stock_code: string
  stock_name: string
  action: 'BUY' | 'SELL' | 'HOLD'
  quantity: number
  price: number
  confidence: number
  reasoning: string
  timestamp: string
  debate_id?: string | null
  opinions?: AgentOpinion[]
}

export interface AgentOpinion {
  agent_name: string
  role_cn?: string
  agent_role?: string
  action: 'BUY' | 'SELL' | 'HOLD'
  quantity: number
  confidence: number
  reasoning: string
}

export interface Debate {
  debate_id: string
  stock_code: string
  stock_name: string
  final_decision: {
    action: 'BUY' | 'SELL' | 'HOLD'
    quantity: number
    confidence: number
    reasoning: string
  } | null
  opinions: AgentOpinion[]
  timestamp: string
}

export interface Position {
  stock_code: string
  stock_name: string
  quantity: number
  sellable_quantity: number
  avg_cost: number
  current_price: number
  market_value: number
  pnl: number
  pnl_percent: number
}

export interface AccountSummary {
  cash: number
  position_value: number
  total_assets: number
  initial_capital: number
  total_pnl: number
  total_pnl_percent: number
  positions: Position[]
}

export interface PortfolioSnapshot {
  cash: number
  position_value: number
  total_assets: number
  timestamp: string
}

export interface RealtimeData {
  stock_code: string
  name: string
  price: number
  open: number
  high: number
  low: number
  prev_close: number
  volume: number
  change: number
  change_percent: number
  timestamp: string
}

export type WSMessage =
  | { type: 'prices'; data: Record<string, RealtimeData> }
  | { type: 'decision'; data: Decision & { executed: boolean; debate_id?: string | null; opinions?: AgentOpinion[] } }
  | { type: 'account'; data: AccountSummary }
