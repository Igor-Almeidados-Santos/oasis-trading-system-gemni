export interface Allocation {
  asset: string;
  percentage: number;
}

export interface PortfolioSummary {
  totalValueBRL: number;
  totalValueUSD: number;
  allocationByAsset: Allocation[];
  realizedPnL30d: number;
  unrealizedPnL: number;
}

export interface Position {
  exchange: string;
  asset: string;
  quantity: number;
  averagePrice: number;
  currentPrice: number;
  pnl: number;
}

export interface ExchangeBreakdown {
  exchange: string;
  positionCount: number;
  marketValueUSD: number;
  unrealizedPnL: number;
}

export type StrategyStatus = 'draft' | 'active' | 'paused';

export interface Strategy {
  id: string;
  name: string;
  status: StrategyStatus;
  type: string;
  parameters: Record<string, number>;
  schedule?: string | null;
  lastRunAt?: string | null;
  nextRunAt?: string | null;
}

export type MetricTimeframe = '1h' | '24h' | '7d' | '30d';

export interface StrategyMetric {
  strategyId: string;
  name: string;
  timeframe: MetricTimeframe;
  grossReturn: number;
  netReturn: number;
  maxDrawdown: number;
  sharpeRatio: number;
  computedAt: string;
}
