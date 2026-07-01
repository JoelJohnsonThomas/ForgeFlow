# Configuration Reference

Every setting is an environment variable loaded via Pydantic Settings
([`forgeflow/config.py`](../forgeflow/config.py)) — this page is the complete
list, generated from that file. Copy `.env.example` to `.env` for local use; in
production, inject these from a secrets manager. Blank **Default** = required or
empty by default.

Startup validation (`Settings.validate_runtime()`) refuses to boot a
production-shaped config with unsafe values — see [SECURITY.md](../SECURITY.md).

## LLM provider

| Variable | Default | Purpose |
|---|---|---|
| `LLM_PROVIDER` | `openai` | `openai` \| `ollama` \| `anthropic` |
| `OPENAI_API_KEY` | — | Required when `LLM_PROVIDER=openai` |
| `OPENAI_MODEL` | `gpt-4o-mini` | Default (cheap) model for agents |
| `OPENAI_MODEL_STRONG` | `gpt-4o` | Strong model for supervisor + judge |
| `ANTHROPIC_API_KEY` | — | Required when `LLM_PROVIDER=anthropic` |
| `ANTHROPIC_MODEL` | `claude-haiku-4-5` | Default Anthropic model |
| `ANTHROPIC_MODEL_STRONG` | `claude-sonnet-4-5` | Strong Anthropic model |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama daemon URL |
| `OLLAMA_MODEL` | `llama3.2:3b` | Default Ollama model |
| `OLLAMA_MODEL_STRONG` | `llama3.1:8b` | Strong Ollama model |

## Database

| Variable | Default | Purpose |
|---|---|---|
| `POSTGRES_URL` | `postgresql+asyncpg://…/forgeflow` | asyncpg DSN for app queries |
| `POSTGRES_SYNC_URL` | `postgresql+psycopg://…/forgeflow` | psycopg3 DSN for the LangGraph checkpointer |
| `POSTGRES_PASSWORD` | — | **Required by docker-compose** |

## API, auth & tokens

| Variable | Default | Purpose |
|---|---|---|
| `API_HOST` / `API_PORT` | `0.0.0.0` / `8000` | Bind address |
| `API_SECRET_KEY` | — | **Required.** Signs JWTs (`openssl rand -hex 32`) |
| `DEV_LOGIN_ENABLED` | `true` | Expose the `/auth/login` dev path; set `false` in prod |
| `DEV_LOGIN_PASSWORD` | — | Shared dev password; required when dev login is on |
| `ACCESS_TOKEN_TTL_HOURS` | `1` | Access-token lifetime |
| `REFRESH_TOKEN_TTL_DAYS` | `30` | Refresh-token lifetime |
| `OIDC_ENABLED` | `false` | Enable `/auth/oidc/exchange` |
| `OIDC_ISSUER` / `OIDC_AUDIENCE` / `OIDC_JWKS_URL` | — | External IdP validation |
| `OIDC_DEFAULT_ROLE` | `viewer` | Role for auto-provisioned OIDC users |
| `DOCS_ENABLED` | `true` | Serve `/docs` + `/redoc`; disable in prod |
| `CORS_ALLOW_ORIGINS` | `localhost:5173,8501` | Exact-origin allowlist — never `*` |
| `TRUSTED_PROXY_COUNT` | `0` | Reverse-proxy hops to trust for client IP |

See [docs/auth.md](auth.md) for the full auth model.

## Resilience & workflow

| Variable | Default | Purpose |
|---|---|---|
| `MAX_RETRIES` | `3` | Connector retry attempts |
| `CIRCUIT_BREAKER_THRESHOLD` | `5` | Failures before the breaker opens |
| `BUDGET_LIMIT_USD` | `5.0` | Per-run LLM spend ceiling |
| `WORKFLOW_RUN_TIMEOUT_SECONDS` | `180` | Hard ceiling on `/workflows/run` → `504` |
| `A2A_DISPATCH_ENABLED` | `true` | Route node invocations through the A2A registry |
| `APPROVAL_ESCALATION_INTERVAL_SECONDS` | `300` | Escalation job tick |
| `APPROVAL_FIRST_ESCALATION_MINUTES` | `30` | → level 1 (manager) |
| `APPROVAL_SECOND_ESCALATION_MINUTES` | `120` | → level 2 (director) |
| `APPROVAL_AUTO_REJECT_MINUTES` | `1440` | → auto-rejected |

## Observability & tracing

| Variable | Default | Purpose |
|---|---|---|
| `TRACING_PROVIDER` | `langsmith` | `langsmith` \| `phoenix` \| `langfuse` \| `none` |
| `LANGCHAIN_TRACING_V2` | `true` | Enable LangSmith tracing |
| `LANGCHAIN_ENDPOINT` | `api.smith.langchain.com` | LangSmith endpoint |
| `LANGCHAIN_API_KEY` | — | LangSmith key (optional) |
| `LANGCHAIN_PROJECT` | `forgeflow` | LangSmith project |
| `OTEL_ENABLED` | `false` | Toggle OpenTelemetry |
| `OTEL_SERVICE_NAME` | `forgeflow-api` | OTel service name |
| `OTEL_ENVIRONMENT` | `development` | `prod` \| `staging` \| `development` (drives startup validation strictness) |
| `OTEL_EXPORTER_ENDPOINT` | `localhost:4318/v1/traces` | OTLP-HTTP endpoint |
| `OTEL_EXPORTER_HEADERS` | — | Comma-separated `k=v` exporter headers |

## Search, notifications & MCP

| Variable | Default | Purpose |
|---|---|---|
| `TAVILY_API_KEY` | — | Real web search (else mock results) |
| `SLACK_BOT_TOKEN` | — | HITL approval cards (`xoxb-…`) |
| `SLACK_DEFAULT_CHANNEL` | — | Default Slack channel |
| `API_PUBLIC_URL` | `http://localhost:8000` | Externally-reachable base for Slack deep-links |
| `MCP_SERVER_HOST` / `MCP_SERVER_PORT` | `0.0.0.0` / `8001` | MCP server bind |
| `API_URL` | `http://localhost:8000` | Used by the Streamlit dashboard |

## Connectors

See the dedicated [connector setup guide](connectors.md). Each connector's env
vars are listed there with how to obtain the credentials.

## Event-driven mode (optional)

| Variable | Default | Purpose |
|---|---|---|
| `EVENTS_PROVIDER` | `none` | `none` \| `redis` \| `kafka` |
| `EVENTS_REDIS_URL` | `redis://localhost:6379/0` | Redis URL |
| `EVENTS_REDIS_STREAM` / `_GROUP` / `_CONSUMER` | `forgeflow:workflows` / `forgeflow` / `forgeflow-api` | Redis Streams config |
| `EVENTS_KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Kafka brokers |
| `EVENTS_KAFKA_TOPIC` / `_GROUP_ID` | `forgeflow.workflows` / `forgeflow` | Kafka config |

## Telemetry (opt-in, off by default)

| Variable | Default | Purpose |
|---|---|---|
| `TELEMETRY_ENABLED` | `false` | Send anonymous event counts |
| `TELEMETRY_WEBHOOK_URL` | — | Receiver (PostHog/Mixpanel/custom) |
| `TELEMETRY_INSTALL_ID` | — | Anonymous install UUID (generated if empty) |
| `TELEMETRY_VERSION` | `0.1.0` | Reported version |

## Test analytics (optional)

| Variable | Default | Purpose |
|---|---|---|
| `TESTRELIC_API_KEY` | — | TestRelic reporter upload key |
| `TESTRELIC_PROJECT_NAME` | `ForgeFlow` | Dashboard project name |
| `TESTRELIC_UPLOAD_STRATEGY` | `batch` | `batch` \| `realtime` |
