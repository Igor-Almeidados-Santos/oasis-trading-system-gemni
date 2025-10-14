import { ChangeEvent, useCallback, useEffect, useMemo, useState } from 'react';
import {
  getExchangeBreakdown,
  getPortfolioPositions,
  getPortfolioSummary,
  getStrategies,
  getTelemetryMetrics,
} from './api';
import type {
  ExchangeBreakdown,
  PortfolioSummary,
  Position,
  Strategy,
  StrategyMetric,
} from './types';
import './App.css';
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';

const ALLOCATION_COLORS = ['#2563eb', '#22c55e', '#f97316', '#a855f7', '#ec4899', '#0ea5e9'];

type LoadState = 'idle' | 'loading' | 'ready';

const currencyFormatterUSD = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: 2,
});

const currencyFormatterBRL = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
  minimumFractionDigits: 2,
});

const quantityFormatter = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 0,
  maximumFractionDigits: 6,
});

const priceFormatter = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 4,
});

const sharpeFormatter = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

function formatPnL(value: number): string {
  const prefix = value >= 0 ? '+' : '-';
  const formatted = currencyFormatterUSD.format(Math.abs(value));
  return `${prefix}${formatted}`;
}

function formatPercentage(value: number): string {
  const prefix = value >= 0 ? '+' : '-';
  const formatted = (Math.abs(value) * 100).toFixed(2);
  return `${prefix}${formatted}%`;
}

function formatDrawdown(value: number): string {
  return `-${(Math.abs(value) * 100).toFixed(2)}%`;
}

function formatDateTime(value?: string | null): string {
  if (!value) {
    return '—';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return '—';
  }
  return date.toLocaleString('pt-BR', {
    hour12: false,
  });
}

function statusClass(status: string): string {
  switch (status) {
    case 'active':
      return 'badge badge-active';
    case 'paused':
      return 'badge badge-paused';
    default:
      return 'badge badge-draft';
  }
}

function statusLabel(status: string): string {
  switch (status) {
    case 'active':
      return 'Ativa';
    case 'paused':
      return 'Pausada';
    default:
      return 'Rascunho';
  }
}

function metricClass(value: number): string {
  return value >= 0 ? 'metric-positive' : 'metric-negative';
}

function App() {
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [allPositions, setAllPositions] = useState<Position[]>([]);
  const [positions, setPositions] = useState<Position[]>([]);
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [metrics, setMetrics] = useState<StrategyMetric[]>([]);
  const [exchangeBreakdown, setExchangeBreakdown] = useState<ExchangeBreakdown[]>([]);
  const [selectedExchange, setSelectedExchange] = useState<string>('all');
  const [loadState, setLoadState] = useState<LoadState>('idle');
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);

  const fetchData = useCallback(async ({ initial = false } = {}) => {
    if (initial) {
      setLoadState('loading');
    } else {
      setIsRefreshing(true);
    }
    setError(null);

    try {
      const since = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString();
      const [summaryData, positionsData, strategiesData, metricsData, exchangesData] = await Promise.all([
        getPortfolioSummary(),
        getPortfolioPositions(),
        getStrategies(),
        getTelemetryMetrics({ since }),
        getExchangeBreakdown(),
      ]);

      setSummary(summaryData);
      setAllPositions(positionsData);
      setStrategies(strategiesData);
      setMetrics(metricsData);
      setExchangeBreakdown(exchangesData);
      setLastUpdated(new Date());
      setLoadState('ready');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Falha ao carregar dados do dashboard.';
      setError(message);
      setLoadState('ready');
    } finally {
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    if (selectedExchange === 'all') {
      setPositions(allPositions);
      return;
    }

    const filtered = allPositions.filter(
      (position) => position.exchange.toLowerCase() === selectedExchange.toLowerCase(),
    );
    setPositions(filtered);
  }, [allPositions, selectedExchange]);

  useEffect(() => {
    fetchData({ initial: true });
    const interval = setInterval(() => fetchData(), 20000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const allocationData = useMemo(
    () => summary?.allocationByAsset.map((item) => ({
      name: item.asset,
      value: Number(item.percentage.toFixed(2)),
    })) ?? [],
    [summary],
  );

  const sortedPositions = useMemo(
    () =>
      [...positions].sort((a, b) => Math.abs(b.pnl) - Math.abs(a.pnl)),
    [positions],
  );

  const exchangeOptions = useMemo(() => {
    const unique = new Set<string>();
    exchangeBreakdown.forEach((item) => unique.add(item.exchange));
    if (unique.size === 0) {
      allPositions.forEach((position) => unique.add(position.exchange));
    }
    return Array.from(unique).sort();
  }, [exchangeBreakdown, allPositions]);

  const activeStrategies = useMemo(
    () => strategies.filter((strategy) => strategy.status === 'active'),
    [strategies],
  );

  const metrics24h = useMemo(() => {
    const latestPerStrategy = new Map<string, StrategyMetric>();

    metrics
      .filter((metric) => metric.timeframe === '24h')
      .forEach((metric) => {
        const current = latestPerStrategy.get(metric.strategyId);
        if (!current || new Date(metric.computedAt) > new Date(current.computedAt)) {
          latestPerStrategy.set(metric.strategyId, metric);
        }
      });

    return Array.from(latestPerStrategy.values());
  }, [metrics]);

  const isLoading = loadState === 'loading' && !summary;
  const hasData = summary !== null;
  const totalOpenPositions = allPositions.length;
  const filteredExchangeLabel = selectedExchange === 'all' ? 'Todas as exchanges' : selectedExchange;

  const handleExchangeChange = useCallback((event: ChangeEvent<HTMLSelectElement>) => {
    setSelectedExchange(event.target.value);
  }, []);

  return (
    <div className="dashboard-container">
      <aside className="sidebar">
        <h2>Oasis</h2>
        <ul className="nav">
          <li className="active">Dashboard</li>
          <li>Operações</li>
          <li>Configurações</li>
        </ul>
      </aside>

      <main className="main-content">
        <header className="header">
          <div>
            <h1>Visão Geral</h1>
            {lastUpdated && (
              <span className="last-updated">
                Atualizado às {lastUpdated.toLocaleTimeString('pt-BR', { hour12: false })}
              </span>
            )}
          </div>
          <div className="header-actions">
            <div
              className={`status-indicator ${
                error ? 'status-error' : isLoading ? 'status-loading' : 'operational'
              }`}
            >
              {error ? 'API Offline' : isLoading ? 'Carregando' : 'Operacional'}
            </div>
            <button
              className="refresh-button"
              onClick={() => fetchData()}
              disabled={isRefreshing}
            >
              {isRefreshing ? 'Atualizando…' : 'Atualizar'}
            </button>
          </div>
        </header>

        {error && <div className="error-message">{error}</div>}
        {isLoading && <div className="loading-message">Carregando dados do portfólio…</div>}

        {hasData && summary && (
          <>
            <section className="kpi-grid">
              <div className="kpi-card">
                <h3>Valor Total (USD)</h3>
                <div className="value">{currencyFormatterUSD.format(summary.totalValueUSD)}</div>
              </div>
              <div className="kpi-card">
                <h3>Valor Total (BRL)</h3>
                <div className="value">{currencyFormatterBRL.format(summary.totalValueBRL)}</div>
              </div>
              <div className="kpi-card">
                <h3>Realizado (30d)</h3>
                <div className={`value ${summary.realizedPnL30d >= 0 ? 'positive' : 'negative'}`}>
                  {formatPnL(summary.realizedPnL30d)}
                </div>
              </div>
              <div className="kpi-card">
                <h3>Não Realizado</h3>
                <div className={`value ${summary.unrealizedPnL >= 0 ? 'positive' : 'negative'}`}>
                  {formatPnL(summary.unrealizedPnL)}
                </div>
              </div>
              <div className="kpi-card">
                <h3>Posições Abertas</h3>
                <div className="value">{totalOpenPositions}</div>
              </div>
              <div className="kpi-card">
                <h3>Estratégias Ativas</h3>
                <div className="value">{activeStrategies.length}</div>
              </div>
            </section>

            <section className="grid-two">
              <div className="card">
                <div className="card-header">
                  <div>
                    <h2>Alocação por Ativo</h2>
                    <p className="card-subtitle">Distribuição percentual do portfólio</p>
                  </div>
                </div>
                {allocationData.length ? (
                  <ResponsiveContainer width="100%" height={260}>
                    <PieChart>
                      <Pie
                        data={allocationData}
                        dataKey="value"
                        nameKey="name"
                        innerRadius={60}
                        outerRadius={100}
                        paddingAngle={2}
                      >
                        {allocationData.map((entry, index) => (
                          <Cell
                            key={entry.name}
                            fill={ALLOCATION_COLORS[index % ALLOCATION_COLORS.length]}
                          />
                        ))}
                      </Pie>
                      <Tooltip
                        formatter={(value: number) => `${value.toFixed(2)}%`}
                        contentStyle={{
                          borderRadius: 8,
                          borderColor: 'var(--border-color)',
                          boxShadow: '0 8px 16px rgba(15, 23, 42, 0.12)',
                        }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="empty-state">Nenhuma alocação disponível.</div>
                )}
              </div>

              <div className="card">
                <div className="card-header">
                  <div>
                    <h2>Posições</h2>
                    <p className="card-subtitle">
                      Preços e PnL por exchange
                      {selectedExchange !== 'all' ? ` • ${filteredExchangeLabel}` : ''}
                    </p>
                  </div>
                  {exchangeOptions.length > 0 && (
                    <div className="card-actions">
                      <label className="filter-label" htmlFor="exchange-filter">
                        Exchange
                      </label>
                      <select
                        id="exchange-filter"
                        className="select-input"
                        value={selectedExchange}
                        onChange={handleExchangeChange}
                      >
                        <option value="all">Todas</option>
                        {exchangeOptions.map((exchange) => (
                          <option key={exchange} value={exchange}>
                            {exchange}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}
                </div>
                {sortedPositions.length ? (
                  <div className="table-wrapper">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Exchange</th>
                          <th>Ativo</th>
                          <th>Quantidade</th>
                          <th>Preço Médio</th>
                          <th>Preço Atual</th>
                          <th>PnL</th>
                        </tr>
                      </thead>
                      <tbody>
                        {sortedPositions.map((position) => (
                          <tr key={`${position.exchange}-${position.asset}`}>
                            <td>{position.exchange}</td>
                            <td>{position.asset}</td>
                            <td>{quantityFormatter.format(position.quantity)}</td>
                            <td>{currencyFormatterUSD.format(position.averagePrice)}</td>
                            <td>{currencyFormatterUSD.format(position.currentPrice)}</td>
                            <td className={position.pnl >= 0 ? 'metric-positive' : 'metric-negative'}>
                              {formatPnL(position.pnl)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="empty-state">Nenhuma posição aberta.</div>
                )}
              </div>
            </section>

            <section className="card">
              <div className="card-header">
                <div>
                  <h2>Resumo por Exchange</h2>
                  <p className="card-subtitle">Exposição agregada e PnL não realizado</p>
                </div>
              </div>
              {exchangeBreakdown.length ? (
                <div className="table-wrapper">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Exchange</th>
                        <th>Posições</th>
                        <th>Valor (USD)</th>
                        <th>PnL Não Realizado</th>
                      </tr>
                    </thead>
                    <tbody>
                      {exchangeBreakdown.map((item) => (
                        <tr key={item.exchange}>
                          <td>{item.exchange}</td>
                          <td>{item.positionCount}</td>
                          <td>{currencyFormatterUSD.format(item.marketValueUSD)}</td>
                          <td
                            className={
                              item.unrealizedPnL >= 0 ? 'metric-positive' : 'metric-negative'
                            }
                          >
                            {formatPnL(item.unrealizedPnL)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="empty-state">Nenhum dado de exchange disponível.</div>
              )}
            </section>

            <section className="card">
              <div className="card-header">
                <div>
                  <h2>Estratégias</h2>
                  <p className="card-subtitle">Status operacional e agenda</p>
                </div>
              </div>
              {strategies.length ? (
                <div className="strategy-grid">
                  {strategies.map((strategy) => (
                    <div className="strategy-card" key={strategy.id}>
                      <div className="strategy-header">
                        <h3>{strategy.name}</h3>
                        <span className={statusClass(strategy.status)}>
                          {statusLabel(strategy.status)}
                        </span>
                      </div>
                      <div className="strategy-meta">
                        <span>Tipo: {strategy.type}</span>
                        <span>Agenda: {strategy.schedule ?? '—'}</span>
                        <span>Última Execução: {formatDateTime(strategy.lastRunAt)}</span>
                        <span>Próxima Execução: {formatDateTime(strategy.nextRunAt)}</span>
                      </div>
                      {Object.keys(strategy.parameters).length > 0 && (
                        <div className="strategy-params">
                          {Object.entries(strategy.parameters).map(([key, value]) => (
                            <span className="param-chip" key={key}>
                              {key}: {priceFormatter.format(value)}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="empty-state">Nenhuma estratégia configurada.</div>
              )}
            </section>

            <section className="card">
              <div className="card-header">
                <div>
                  <h2>Performance das Estratégias (24h)</h2>
                  <p className="card-subtitle">Retornos líquidos e drawdown em janela diária</p>
                </div>
              </div>
              {metrics24h.length ? (
                <div className="table-wrapper">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Estratégia</th>
                        <th>Retorno Bruto</th>
                        <th>Retorno Líquido</th>
                        <th>Drawdown Máx.</th>
                        <th>Sharpe</th>
                        <th>Atualizado em</th>
                      </tr>
                    </thead>
                    <tbody>
                      {metrics24h.map((metric) => (
                        <tr key={`${metric.strategyId}-${metric.timeframe}`}>
                          <td>{metric.name}</td>
                          <td className={metricClass(metric.grossReturn)}>
                            {formatPercentage(metric.grossReturn)}
                          </td>
                          <td className={metricClass(metric.netReturn)}>
                            {formatPercentage(metric.netReturn)}
                          </td>
                          <td className="metric-negative">{formatDrawdown(metric.maxDrawdown)}</td>
                          <td>{sharpeFormatter.format(metric.sharpeRatio)}</td>
                          <td>{formatDateTime(metric.computedAt)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="empty-state">Sem métricas registradas nas últimas 24 horas.</div>
              )}
            </section>
          </>
        )}
      </main>
    </div>
  );
}

export default App;
