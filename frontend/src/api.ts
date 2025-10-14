import type {
  ExchangeBreakdown,
  PortfolioSummary,
  Position,
  Strategy,
  StrategyMetric,
} from './types';

const DEFAULT_BASE_URL = 'http://localhost:8000';
const BASE_URL = (import.meta.env.VITE_BFF_BASE_URL ?? DEFAULT_BASE_URL).replace(/\/$/, '');

interface FetchOptions {
  query?: Record<string, string | undefined>;
  init?: RequestInit;
}

function buildUrl(path: string, query?: Record<string, string | undefined>): string {
  const url = new URL(path, `${BASE_URL}/`);
  if (query) {
    Object.entries(query).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        url.searchParams.set(key, value);
      }
    });
  }
  return url.toString();
}

async function fetchJson<T>(path: string, options: FetchOptions = {}): Promise<T> {
  const { query, init } = options;
  const response = await fetch(buildUrl(path, query), {
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    throw new Error(`Falha ao carregar ${path}: ${response.status} ${response.statusText}`);
  }

  return (await response.json()) as T;
}

export function getPortfolioSummary(): Promise<PortfolioSummary> {
  return fetchJson<PortfolioSummary>('/portfolio/summary');
}

export function getPortfolioPositions(options: { exchange?: string } = {}): Promise<Position[]> {
  return fetchJson<Position[]>('/portfolio/positions', { query: options });
}

export function getStrategies(): Promise<Strategy[]> {
  return fetchJson<Strategy[]>('/strategies');
}

export function getTelemetryMetrics(options: { since?: string } = {}): Promise<StrategyMetric[]> {
  return fetchJson<StrategyMetric[]>('/telemetry/metrics', { query: options });
}

export function getExchangeBreakdown(): Promise<ExchangeBreakdown[]> {
  return fetchJson<ExchangeBreakdown[]>('/portfolio/exchanges');
}
