export interface Signal {
  symbol: string;
  direction: 'long' | 'short';
  score: number;
  mtf_score?: number;
  mtf_aligned?: boolean;
  mtf_details?: any;
  entry_price?: number;
  tp_price?: number;
  sl_price?: number;
  atr?: number;
  trigger_events: string[];
  timestamp: number;
  features_snapshot?: any;
  ai?: any;
  // Performance tracking
  outcome?: 'open' | 'tp_hit' | 'sl_hit' | 'expired' | 'manual' | 'reversed' | null;
  exit_price?: number;
  exit_time?: number;
  return_pct?: number;
  duration_sec?: number;
  // Real-time tracking (for open signals)
  current_price?: number;
  current_pnl_pct?: number;
}

export interface Message {
  id: string;
  type: 'signal' | 'user' | 'assistant' | 'system';
  content: string;
  signal?: Signal;
  timestamp: number;
}

export interface WebSocketMessage {
  type: 'signal' | 'status' | 'connected' | 'keepalive';
  data?: any;
}

export interface SystemMetrics {
  cpu_percent?: number;
  memory_rss_mb?: number;
  memory_percent?: number;
  uptime_seconds?: number;
}

export interface PerformanceStats {
  stats: Array<{
    symbol: string;
    total_signals: number;
    wins: number;
    losses: number;
    win_rate: number;
    avg_return_pct: number;
    avg_duration_sec: number;
  }>;
  timeframe: string;
  lookback_days: number;
}
