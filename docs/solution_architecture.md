# Oasis Crypto Trader — Arquitetura de Referência

## 1. Visão Geral do Sistema
O Oasis Crypto Trader é uma plataforma de automação de negociações multi-estratégia que integra múltiplas exchanges e wallets sob um orçamento operacional de até R$200/mês. A solução prioriza segurança de credenciais, observabilidade nativa e execução resiliente de ordens, suportando crescimento incremental das estratégias do investidor.

### Objetivos Arquiteturais
- **Escalabilidade seletiva:** permitir que execução de estratégias e conectores cresçam de forma independente.
- **Disponibilidade elevada:** atingir 99% de uptime através de redundância leve e monitoramento proativo.
- **Custo controlado:** utilizar componentes gerenciados com foco em infraestrutura containerizada de baixo custo (Docker + VPS/Cloud leve).
- **Governança e segurança:** centralizar gestão de segredos e instrumentar auditoria de operações.

## 2. Contexto do Sistema
```
[Usuário] → [Dashboard Web] → [API Gateway / BFF]
                                 ↓            ↓
                        [Config Service]   [Observability API]
                                 ↓
                  ┌──────────────┴─────────────┐
                  │                            │
         [Strategy Orchestrator]      [Exchange Connector Mesh]
                  ↓                            ↓
         [Risk Engine (gRPC)]      [Execution Service (gRPC)]
                  ↓                            ↓
              [Order Bus (Kafka/NATS)] → [Exchange APIs]
```
- **Usuário:** define estratégias, acompanha métricas.
- **Dashboard Web (Next.js):** interface centrada em UX com streaming de métricas via WebSockets.
- **API Gateway/BFF (FastAPI):** expõe REST e WebSocket para o front e delega chamadas a microserviços.
- **Strategy Orchestrator:** agenda execuções, avalia sinais e publica no barramento.
- **Risk Engine / Execution Service:** componentes desacoplados via gRPC seguindo contrato existente (`contracts/trading_system.proto`).
- **Observability Stack:** Prometheus + Grafana + Loki para métricas, dashboards e logs centralizados.
- **Data Stores:** PostgreSQL (configurações e auditoria), Redis (cache/session), TimescaleDB/InfluxDB (séries temporais de métricas), MinIO/S3 (snapshot de datasets para backtesting).

## 3. Domínios e Serviços
| Domínio                   | Serviço/Componente         | Responsabilidades-Chave |
|---------------------------|----------------------------|--------------------------|
| Identidade & Segurança    | Auth Service               | Autenticação via OAuth2/passwordless, MFA opcional, controle de sessões Web.
|                           | Secrets Vault              | Armazenamento cifrado de chaves de API (HashiCorp Vault ou AWS Secrets Manager).
| Estratégias               | Strategy Orchestrator      | CRUD de estratégias, agendamento (APScheduler/Celery), versionamento, replay/backtest.
| Execução & Conectividade  | Risk Engine (gRPC)         | Validação de risco (limites de exposição, stop loss, sizing dinâmico).
|                           | Execution Service (gRPC)   | Tradução de ordens padrão para APIs específicas das exchanges, gestão de retries.
|                           | Connector Adapters         | Implementações específicas por exchange/wallet com testes de contrato.
| Monitoramento & Dados     | Telemetry Collector        | Recebe métricas/logs via OpenTelemetry, enfileira em Prometheus/Loki.
|                           | Portfolio Aggregator       | Consolida posições de múltiplas exchanges, expõe visão unificada via API.
| Experiência do Usuário    | Dashboard Web (Next.js)    | Visualizações responsivas, alertas, configuração assistida.

## 4. Stack Tecnológica Recomendada
- **Backend:** Python 3.11 (FastAPI para BFF, gRPC para serviços internos), Poetry para gerenciamento de dependências.
- **Mensageria:** NATS JetStream (leve, baixo custo) ou Apache Kafka (se volume de eventos crescer).
- **Banco Relacional:** PostgreSQL 15 com extensões TimescaleDB para métricas históricas.
- **Cache/Mensagens rápidas:** Redis 7 (autogerenciado ou serviço gerenciado low-cost).
- **Front-end:** Next.js 14 com TailwindCSS e Zustand para estado.
- **Infraestrutura:** Docker Compose para desenvolvimento, Kubernetes leve (k3s) ou ECS Fargate para produção simples.
- **CI/CD:** GitHub Actions com pipelines de testes (pytest, mypy, eslint) e deploy automatizado via ArgoCD/GitOps.
- **Observabilidade:** OpenTelemetry SDK → Collector → Prometheus, Loki, Grafana. Alertmanager para alertas proativos.

## 5. Fluxos Principais
### 5.1 Execução de Estratégia
1. Usuário cria estratégia no dashboard → API BFF grava configuração no PostgreSQL.
2. Scheduler do Strategy Orchestrator ativa execução conforme cronograma.
3. Estratégia gera `TradingSignal` → envia ao Risk Engine via gRPC (`ProcessSignal`).
4. Risk Engine valida limites e emite `OrderRequest` para Execution Service.
5. Execution Service traduz ordem para API da exchange e acompanha status.
6. Resposta (`OrderResponse`) é publicada no Order Bus e armazenada para auditoria.
7. Observability Collector anexa métricas (latência, sucesso) para dashboards.

### 5.2 Atualização de Dashboard
1. Portfolio Aggregator coleta saldos e posições periodicamente (workers assíncronos).
2. Dados consolidados armazenados em PostgreSQL/Timescale.
3. API BFF expõe endpoint REST `/portfolio/summary` e canal WebSocket para atualizações.
4. Front-end atualiza visualizações e gera alertas locais.

### 5.3 Onboarding de Nova Exchange
1. Desenvolvedor implementa novo `Connector Adapter` obedecendo interface de contrato.
2. Testes de contrato garantem conformidade (mock API / sandbox da exchange).
3. Deploy com feature flag habilita gradualmente a exchange para o usuário.

## 6. Qualidade, Segurança e Operações
- **TDD e Coverage:** suites de testes para cada domínio; integração contínua bloqueia merge sem cobertura mínima de 80%.
- **Segurança:** armazenamento de credenciais cifradas (Vault + Transit Engine), rotação periódica, assinatura de mensagens.
- **Compliance:** logs de auditoria imutáveis (Loki + retenção), alinhamento a LGPD para dados pessoais.
- **Observabilidade:** tracing distribuído entre BFF, Strategy Orchestrator e serviços gRPC; dashboards padrão (latência, taxa de sucesso, drawdown).
- **Resiliência:** circuit breakers (resilient-python), retries exponenciais, uso de dead-letter queue para ordens falhas.
- **Custos:** monitoramento de uso de recursos, escalonamento programável (cron) para desligar componentes fora do horário crítico.

## 7. Próximos Passos
1. Elaborar contratos de API REST para o Dashboard (OpenAPI) e workers (gRPC adicional para telemetria).
2. Definir modelo de dados lógico no PostgreSQL/Timescale e migrações iniciais.
3. Configurar pipelines de CI/CD conforme stack acima.
4. Planejar sprint inicial com foco em Strategy Orchestrator + integração com Risk/Execution existentes.
