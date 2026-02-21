export interface StatusData {
  state: string;
  balance: number;
  peak_balance: number;
  total_trades: number;
  wins: number;
  losses: number;
  consecutive_losses: number;
  win_rate: number;
  total_signals: number;
  signals_traded: number;
  dry_run: boolean;
  uptime_seconds: number;
}

export interface PriceHistory {
  price: number;
  ts: number;
}

export interface MarketData {
  question: string | null;
  up_price: number;
  down_price: number;
  window_start: number;
  window_end: number;
  window_remaining: number;
  active: boolean;
}

export interface PriceData {
  btc_price: number;
  oracle_price: number;
  momentum_pct: number;
  oracle_divergence_pct: number;
  oracle_lag_seconds: number;
  trend_consistent: boolean;
  window_size: number;
  history: PriceHistory[];
  market: MarketData;
}

export interface Trade {
  id: number;
  timestamp: number;
  side: string;
  amount_usdc: number;
  price: number;
  confidence: number;
  condition_id: string;
  order_id: string;
  success: boolean;
  dry_run: boolean;
  outcome: string;
  payout: number;
}

export interface TradesData {
  trades: Trade[];
  total: number;
}

export interface BalanceEntry {
  timestamp: number;
  balance: number;
  event: string;
}

export interface BalanceData {
  current: number;
  initial: number;
  peak: number;
  history: BalanceEntry[];
}

export interface GateStatus {
  passed: boolean;
  value: number;
  threshold?: number;
  min?: number;
  max?: number;
  lag_seconds?: number;
}

export interface ActiveSignal {
  side: string;
  confidence: number;
  momentum_pct: number;
  target_price: number;
  binance_price: number;
}

export interface SignalData {
  gates: {
    timing: GateStatus;
    momentum: GateStatus;
    oracle_lag: GateStatus & { lag_seconds: number };
    market_price: GateStatus;
    confidence: GateStatus;
  };
  active_signal: ActiveSignal | null;
  total_signals: number;
  signals_traded: number;
}

export interface RiskData {
  can_trade: boolean;
  reason: string;
  drawdown: number;
  drawdown_limit: number;
  consecutive_losses: number;
  max_consecutive_losses: number;
  cooldown_remaining: number;
  cooldown_minutes: number;
  position_tier: string;
  next_bet_size: number;
  stop_loss: number;
  target_balance: number;
}
