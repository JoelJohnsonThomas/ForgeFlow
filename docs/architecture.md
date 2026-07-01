# Architecture

ForgeFlow orchestrates a **supervisor multi-agent system** behind a FastAPI
service, with durable state in PostgreSQL and tools exposed over the Model
Context Protocol (MCP). This page explains how the pieces fit together, with
diagrams.

## High-level components

```mermaid
flowchart TB
    subgraph Client
        UI[React 19 Console<br/>nginx :8501]
    end
    subgraph API[FastAPI :8000]
        MW[Middleware chain<br/>RBAC · RateLimit · Security · Audit]
        RT[Routers<br/>workflows · approvals · auth · …]
        GR[LangGraph graphs<br/>sales_ops · support_ops · finance_recon]
    end
    subgraph Tools[MCP Server :8001]
        TR[14 tool routers]
    end
    subgraph Data
        PG[(PostgreSQL 16<br/>+ pgvector)]
    end
    EXT[Enterprise APIs<br/>HubSpot · Jira · SAP · …]
    LLM[LLM provider<br/>OpenAI · Anthropic · Ollama]
    OBS[Observability<br/>LangSmith · OTel · Prometheus]

    UI -->|/api/* JWT| MW --> RT --> GR
    GR -->|checkpoints, runs| PG
    GR -->|tool calls| TR
    TR -->|SSRF-guarded| EXT
    GR --> LLM
    RT --> PG
    API --> OBS
```

- **Console** — React SPA served by nginx; talks to the API with a per-user JWT.
- **API** — stateless; the middleware chain authenticates + guards every request,
  routers dispatch to compiled LangGraph graphs.
- **Graphs** — one compiled `StateGraph` per workflow type, checkpointed to
  Postgres so any worker resumes any `thread_id`.
- **MCP server** — exposes connectors + utilities as tools; every outbound URL is
  SSRF-guarded.
- **PostgreSQL** — the only stateful component (runs, approvals, memory, auth,
  checkpoints). See [database.md](database.md).

## API request lifecycle

Middleware runs outermost-first on the request, reverse on the response:

```mermaid
flowchart LR
    Req[Request] --> SH[SecurityHeaders]
    SH --> RBAC{RBAC<br/>JWT + role}
    RBAC -->|401/403| Rej[Reject]
    RBAC --> RL{RateLimit}
    RL -->|429| Rej
    RL --> SEC[Security<br/>PII redact + prompt guard]
    SEC -->|high-risk 400| Rej
    SEC --> AUD[Audit log]
    AUD --> H[Route handler]
    H --> Resp[Response + headers]
```

- **SecurityHeaders** — HSTS/CSP/XFO/etc. on every response (incl. errors).
- **RBAC** — verifies the bearer JWT, maps `(method, path)` → permission
  (longest-prefix, deny-by-default). No header fallback — fail closed.
- **RateLimit** → **Security** (PII redaction + prompt-injection scan) → **Audit**
  (append-only log) → handler.

## Workflow execution (the `sales_ops` graph)

```mermaid
flowchart TD
    START([run]) --> SUP{Supervisor<br/>routing decision}
    SUP -->|research| RES[Researcher<br/>web search · scrape · enrich]
    RES --> SUP
    SUP -->|analyze| ANA[Analyzer<br/>0–10 ICP score + risk]
    ANA --> SUP
    SUP -->|propose| EXE[Executor<br/>draft proposal]
    EXE --> HA{{human_approval<br/>interrupt}}
    HA -->|approve| DONE([execute + complete])
    HA -->|reject| REJ([rejected])
    SUP -->|done| DONE

    RES -.checkpoint.-> PG[(Postgres)]
    ANA -.checkpoint.-> PG
    EXE -.checkpoint.-> PG
```

The **supervisor** emits a structured `RoutingDecision` (it never calls tools
directly), keeping routing deterministic and auditable. Every node is
checkpointed; at `human_approval` the graph **interrupts** and persists — a later
`/approvals/{token}/approve` resumes from the checkpoint. `dry_run` executes the
full LLM plan but skips side effects.

## Agent lifecycle & A2A

```mermaid
sequenceDiagram
    participant S as Supervisor
    participant R as Researcher
    participant A as Analyzer
    participant E as Executor
    participant M as MCP tools
    S->>R: route(research)
    R->>M: web_search / scrape_url (SSRF-guarded)
    M-->>R: results (wrapped as UNTRUSTED_TOOL_OUTPUT)
    R-->>S: research_results
    S->>A: route(analyze)
    A-->>S: analysis_scores (ICP 0–10 + risk)
    S->>E: route(propose)
    E->>M: crm / email tools
    E-->>S: proposal
    S->>S: interrupt → human approval
```

Agents also expose an **A2A** (Agent-to-Agent) interface — JSON-RPC 2.0 with
`AgentCard` capability discovery and an in-workflow dispatch registry
([`forgeflow/a2a/`](../forgeflow/a2a/)), so nodes can be deployed out-of-process.

## Authentication flow

```mermaid
sequenceDiagram
    participant C as Client
    participant API
    participant DB as auth_users / auth_refresh_tokens
    C->>API: POST /auth/login {user, password, mfa_code?}
    API->>DB: verify Argon2 hash (+ TOTP if enabled)
    API-->>C: {access_token (JWT, 1h), refresh_token (30d)}
    Note over C,API: later, when access expires
    C->>API: POST /auth/refresh {refresh_token}
    API->>DB: rotate family (reuse → revoke family)
    API-->>C: new access + refresh
```

Production fronts the API with an OIDC IdP via `/auth/oidc/exchange` (RS256/JWKS
verification + JIT provisioning). Full model: [auth.md](auth.md).

## Key design decisions

| Decision | Why |
|---|---|
| Supervisor emits routing, never calls tools | Deterministic, auditable control flow |
| Postgres checkpointer | Crash-safe, horizontally scalable resume |
| Tools over MCP | Swap a mock connector for a real one without touching agent code |
| Tool output wrapped `UNTRUSTED_TOOL_OUTPUT` | Blunts 2nd-order prompt injection |
| Connectors degrade to mocks | Demos/CI run without real credentials |
| Fail-closed RBAC + startup validation | Insecure configs can't serve traffic |

## Deployment topology

```mermaid
flowchart LR
    LB[Load balancer / Ingress] --> FE[Console pods]
    LB --> API[API pods 2–10]
    API --> MCP[MCP pods 1–5]
    API --> DB[(Managed Postgres<br/>PITR + snapshots)]
    MCP --> DB
```

See the [deployment section](../README.md#-deployment) and
[backup-dr.md](operations/backup-dr.md).
