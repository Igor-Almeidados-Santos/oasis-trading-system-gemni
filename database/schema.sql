CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Cria a tabela para armazenar todas as ordens enviadas
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    client_order_id VARCHAR(255) UNIQUE NOT NULL,
    exchange_order_id VARCHAR(255),
    exchange VARCHAR(50) NOT NULL DEFAULT 'UNKNOWN',
    product_id VARCHAR(20) NOT NULL,
    side VARCHAR(4) NOT NULL,
    quantity DECIMAL(20, 10) NOT NULL,
    price DECIMAL(20, 10) NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Tabela para armazenar o estado da estratégia
CREATE TABLE IF NOT EXISTS strategy_state (
    id SERIAL PRIMARY KEY,
    product_id VARCHAR(20) UNIQUE NOT NULL,
    grid_state JSONB NOT NULL, -- Armazena o dicionário da grade como um JSON
    last_price DECIMAL(20, 10),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Tabela para armazenar as execuções (fills) de cada ordem
CREATE TABLE IF NOT EXISTS fills (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id),
    exchange_trade_id VARCHAR(255) UNIQUE NOT NULL,
    price DECIMAL(20, 10) NOT NULL,
    quantity DECIMAL(20, 10) NOT NULL,
    commission DECIMAL(20, 10),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Tabela de estratégias orquestradas pelo sistema
CREATE TABLE IF NOT EXISTS strategies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    parameters JSONB NOT NULL,
    schedule TEXT,
    last_run_at TIMESTAMPTZ,
    next_run_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (status IN ('draft', 'active', 'paused'))
);

CREATE INDEX IF NOT EXISTS idx_strategies_status ON strategies(status);

-- Métricas agregadas para monitoramento de performance das estratégias
CREATE TABLE IF NOT EXISTS strategy_metrics (
    id BIGSERIAL PRIMARY KEY,
    strategy_id UUID NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,
    timeframe TEXT NOT NULL,
    gross_return DECIMAL(18, 8) NOT NULL,
    net_return DECIMAL(18, 8) NOT NULL,
    max_drawdown DECIMAL(18, 8) NOT NULL,
    sharpe_ratio DECIMAL(18, 8) NOT NULL,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_strategy_metrics_strategy_timeframe
    ON strategy_metrics(strategy_id, timeframe);
