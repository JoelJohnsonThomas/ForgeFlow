<div align="center">

# ⚡ ForgeFlow

### Production-grade Multi-Agent Enterprise Workflow Orchestrator

**Ship a team of specialized AI agents — with human-in-the-loop approvals, full observability, real enterprise connectors, and defense-in-depth security — to production.**

[![CI](https://github.com/JoelJohnsonThomas/forgeflow/actions/workflows/ci.yml/badge.svg)](https://github.com/JoelJohnsonThomas/forgeflow/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2.60+-1c7d4d.svg)](https://langchain-ai.github.io/langgraph/)
[![MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-purple.svg)](https://modelcontextprotocol.io)
[![React 19](https://img.shields.io/badge/React-19-61dafb.svg)](https://react.dev)
[![Docker](https://img.shields.io/badge/docker-compose-2496ed.svg)](https://docker.com)
[![Tests](https://img.shields.io/badge/tests-306%20passing-brightgreen.svg)](tests/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

[Quickstart](#-quickstart) · [Architecture](#-architecture) · [Features](#-features) · [API](#-api-reference) · [Deployment](#-deployment) · [Roadmap](#-roadmap) · [Contributing](#-contributing)

![ForgeFlow Console](docs/images/dashboard.png)

</div>

---

## 📖 Table of Contents

- [What is ForgeFlow?](#-what-is-forgeflow)
- [Why ForgeFlow?](#-why-forgeflow)
- [Screenshots](#-screenshots)
- [Features](#-features)
- [Architecture](#-architecture)
- [Technology Stack](#-technology-stack)
- [Quickstart](#-quickstart)
- [Configuration](#-configuration)
- [Usage Examples](#-usage-examples)
- [Workflows & Connectors](#-workflows--connectors)
- [API Reference](#-api-reference)
- [Security](#-security)
- [Performance & Scalability](#-performance--scalability)
- [Deployment](#-deployment)
- [Developer Guide](#-developer-guide)
- [Project Structure](#-project-structure)
- [Roadmap](#-roadmap)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🧭 What is ForgeFlow?

**ForgeFlow** is an open-source platform for building, running, and operating **multi-agent AI workflows** in the enterprise. Instead of a single monolithic prompt, ForgeFlow orchestrates a **supervisor agent** that routes work to a team of specialists — a researcher, an analyzer, and an executor — each grounded in real tools and real data, and gated by **human approval** before any high-impact side effect.

It ships three named workflow domains out of the box:

| Workflow | Pipeline | Status | Connector |
|---|---|---|---|
| **`sales_ops`** | qualify → research → analyze → propose → **approve** → execute | ✅ **Production** | HubSpot CRM (upsert-by-email, idempotent deals, 429 backoff) |
| **`support_ops`** | triage → investigate → respond → escalate → resolve | ⚠️ Template scaffold | Pairs with Jira / ServiceNow |
| **`finance_recon`** | ingest → match → flag variance → approve → post | ⚠️ Template scaffold | Pairs with QuickBooks / SAP |

> `support_ops` and `finance_recon` are honest scaffolds — they raise on `.run()` unless `dry_run=True` or `FORGEFLOW_ALLOW_TEMPLATE_WORKFLOWS=1` is set, and the React console labels them as such. Three named templates ≠ three production workflows. `sales_ops` is the fully-wired reference path: follow [docs/sales-ops-production.md](docs/sales-ops-production.md) to run it against a real HubSpot account on Fly.io in under an hour.

### The problem it solves

Most "agent demos" collapse the moment they meet production reality: there's no audit trail, no cost ceiling, no way to pause for a human, secrets leak into prompts, a single flaky API takes down the whole run, and swapping a mock tool for a real one means rewriting the agent. ForgeFlow is the **opinionated reference implementation** of everything that sits *around* the LLM call to make agentic automation safe to deploy:

- **Durable state** — every node is checkpointed to PostgreSQL, so any worker can resume any run after a crash.
- **Human-in-the-loop** — workflows pause via LangGraph `interrupt_before` and resume on an approve/reject webhook or Slack button.
- **Pluggable tools** — agents talk to the world through the **Model Context Protocol (MCP)**, so you swap a mock CRM for HubSpot without touching agent code.
- **Defense in depth** — PII redaction, prompt-injection guards, SSRF protection, untrusted-tool-output quarantine, and an outbound-email allowlist.
- **Cost & resilience controls** — per-run budget guard, circuit breakers, retry-with-backoff, and token-level cost tracking.
- **Full observability** — LangSmith / Phoenix / Langfuse tracing, Prometheus metrics, immutable audit log, and LLM-as-judge evaluation.

### Who it's for

| Audience | What ForgeFlow gives you |
|---|---|
| **Platform / ML engineers** | A batteries-included blueprint for shipping agents with checkpointing, RBAC, observability, and connectors already wired. |
| **Enterprises** | Human approvals, audit trails, cost ceilings, multi-tenancy, and on-prem / air-gapped deployment paths. |
| **OSS contributors** | A clean, typed, well-tested (306 tests) codebase with clear extension points — connectors, MCP tools, and workflow templates. |
| **Recruiters & evaluators** | A demonstration of production agentic-AI engineering: LangGraph, MCP, A2A, Kubernetes, Terraform, and a polished React 19 console. |

---

## 💎 Why ForgeFlow?

- 🧠 **Supervisor multi-agent orchestration** — deterministic, auditable hub-and-spoke routing built on LangGraph `StateGraph`.
- 🔌 **8 real enterprise connectors** — HubSpot, Salesforce, Jira, ServiceNow, GitHub, SAP S/4HANA, QuickBooks Online, and Microsoft Graph — all behind a single resilient connector base.
- 🛡️ **Security-first by design** — see [SECURITY_AUDIT.md](SECURITY_AUDIT.md) for the full threat model and the fixes that close each finding.
- 🔁 **Provider-agnostic** — OpenAI, Anthropic Claude, or a fully local **Ollama** daemon (privacy / air-gapped mode).
- 📊 **Operate it, don't just run it** — a 13-view React console for runs, approvals, cost, audit, memory, agents, and evaluations.
- 🚢 **Deploy anywhere** — Docker Compose, Kubernetes, Helm, Terraform (AWS), Fly.io, and an offline bundle for air-gapped sites.

---

## 📸 Screenshots

> Replace these renders with live captures of your own deployment.

| Landing & marketing page | Operations console |
|---|---|
| ![Landing page](docs/images/index.png) | ![Console dashboard](docs/images/dashboard.png) |

| System overview | Architecture deep-dive |
|---|---|
| ![System overview](docs/images/system.png) | ![Architecture page](docs/images/architecture.png) |

<details>
<summary><b>Suggested screenshots to capture for your fork</b></summary>

- `docs/images/dashboard.png` — `/console` operations overview (KPI strip + recent runs)
- `docs/images/live-run.png` — `/console/runs` Gantt timeline + tool trace tree
- `docs/images/approvals.png` — `/console/approvals` queue with approve/reject
- `docs/images/cost.png` — `/console/cost` per-agent and per-workflow breakdown
- `docs/images/architecture.png` — `/architecture` 8-section system deep-dive

</details>

---

## ✨ Features

<details open>
<summary><b>🤖 AI-Powered Multi-Agent Development</b></summary>

- **Supervisor agent** emits a structured `RoutingDecision` (never calls tools directly) so routing stays deterministic and auditable — [forgeflow/agents/supervisor.py](forgeflow/agents/supervisor.py)
- **Researcher agent** — web search + URL scraping + enrichment, with SSRF-guarded fetches
- **Analyzer agent** — 0–10 ICP scoring with risk flags and a recommended action
- **Executor agent** — drafts proposals, writes to the CRM, and sends pinned-recipient email
- **Pluggable LLM providers** — OpenAI (default), Anthropic Claude, or local Ollama via a single `get_model()` factory — [forgeflow/models/provider.py](forgeflow/models/provider.py)
- **Agent-to-Agent (A2A) protocol** — JSON-RPC 2.0, `AgentCard` capability discovery, and an in-workflow dispatch registry — [forgeflow/a2a/](forgeflow/a2a/)

</details>

<details>
<summary><b>🔄 Workflow Automation & Orchestration</b></summary>

- **LangGraph `StateGraph`** with PostgreSQL checkpointing — every node persisted, any worker resumes any `thread_id` — [forgeflow/graph/](forgeflow/graph/)
- **Human-in-the-loop** via `interrupt_before` + approve/reject webhooks and Slack deep-link buttons — [forgeflow/api/routers/approvals.py](forgeflow/api/routers/approvals.py)
- **Approval escalation** — a background job ratchets stale approvals through level 1 → 2 → auto-reject — [forgeflow/jobs/escalation.py](forgeflow/jobs/escalation.py)
- **SSE streaming** — stream agent reasoning + tool calls live with `astream()` over `StreamingResponse`
- **Event-driven mode** — consume **Redis Streams** or **Kafka** events into a shared `EventDispatcher` — [forgeflow/events/](forgeflow/events/)
- **Dry-run simulation** — run the full LLM plan with all side effects (CRM writes, emails, Slack) skipped
- **Workflow template marketplace** — file-based registry with a `manifest.yaml` schema and a CLI validator — [forgeflow/marketplace/](forgeflow/marketplace/), [templates/](templates/)

</details>

<details>
<summary><b>🧪 Testing, Evaluation & Validation</b></summary>

- **306 tests** across unit + integration suites — [tests/](tests/)
- **LLM-as-judge evaluation** — faithfulness, relevance, coherence, and hallucination detection in one pass — [forgeflow/evaluation/judge.py](forgeflow/evaluation/judge.py)
- **Eval regression gate in CI** — `.github/workflows/eval.yml` checks scores against a baseline ([tests/eval_baseline.json](tests/eval_baseline.json))
- **HubSpot pre-flight validator** — probes your real CRM end-to-end before deploy — [scripts/validate_hubspot.py](scripts/validate_hubspot.py)
- **Type + lint gates** — `ruff` (E/F/I/UP/B/SIM/ANN) and `mypy` enforced in CI

</details>

<details>
<summary><b>🛡️ Security (Defense in Depth)</b></summary>

- **PII redactor** — conservative regex scrubbing of common identifiers — [forgeflow/security/pii_redactor.py](forgeflow/security/pii_redactor.py)
- **Prompt-injection guard** — heuristic risk scoring on inbound text — [forgeflow/security/prompt_guard.py](forgeflow/security/prompt_guard.py)
- **SSRF guard** — blocks private IPs, IMDS, and non-http(s) schemes on every agent-controlled URL — [forgeflow/security/ssrf_guard.py](forgeflow/security/ssrf_guard.py)
- **Tool-output quarantine** — wraps tool results in an `<UNTRUSTED_TOOL_OUTPUT>` envelope to defeat 2nd-order injection — [forgeflow/security/tool_output_guard.py](forgeflow/security/tool_output_guard.py)
- **Outbound-email allowlist** — pins recipients so an LLM can't exfiltrate via `email_send` — [forgeflow/security/email_allowlist.py](forgeflow/security/email_allowlist.py)
- **JWT + RBAC**, immutable partitioned **audit log**, **rate limiting**, and a CORS allowlist (never `*`) — [forgeflow/middleware/](forgeflow/middleware/)

</details>

<details>
<summary><b>📈 Observability & Cost Control</b></summary>

- **Tracing** — pick LangSmith, Phoenix, Langfuse, or none via `TRACING_PROVIDER`; OTel auto-configures for OTLP backends — [forgeflow/observability/tracing_provider.py](forgeflow/observability/tracing_provider.py)
- **Prometheus** — `/metrics/prometheus` exposition endpoint
- **Cost tracking** — `tiktoken`-based token counting with a per-model cost table and per-agent breakdown — [forgeflow/observability/cost_tracker.py](forgeflow/observability/cost_tracker.py)
- **Budget guard** — halts a workflow before projected spend exceeds `BUDGET_LIMIT_USD` — [forgeflow/resilience/budget_guard.py](forgeflow/resilience/budget_guard.py)
- **Circuit breaker** — CLOSED/OPEN/HALF_OPEN state machine stops cascading failures — [forgeflow/resilience/circuit_breaker.py](forgeflow/resilience/circuit_breaker.py)
- **Opt-in anonymous telemetry** — off by default, PII-clean allowlist — [forgeflow/telemetry/](forgeflow/telemetry/)

</details>

<details>
<summary><b>🏢 Enterprise & Platform</b></summary>

- **Multi-tenancy** — `workspaces` as the tenant root with a nullable `workspace_id` on every tenant-scoped row (query scoping in progress) — [forgeflow/api/routers/workspaces.py](forgeflow/api/routers/workspaces.py)
- **Multi-modal input** — PDF text extraction + vision-LLM image description — [forgeflow/multimodal/](forgeflow/multimodal/)
- **Semantic memory** — pgvector cosine recall, namespace-scoped — [forgeflow/memory/pgvector_store.py](forgeflow/memory/pgvector_store.py)
- **Deployment targets** — Docker Compose, Kubernetes, Helm, Terraform (AWS), Fly.io, and an air-gapped offline bundle

</details>

---

## 🏗️ Architecture

ForgeFlow is a **hub-and-spoke** system: a FastAPI control plane drives a checkpointed LangGraph state machine, agents reach the outside world only through an MCP tool server, and a React console operates the whole thing.

```mermaid
graph TB
    subgraph Client["🖥️ Presentation"]
        Console["React 19 Console :8501<br/>13 views · landing · architecture"]
    end

    subgraph ControlPlane["⚙️ Control Plane — FastAPI :8000"]
        API["REST + SSE API"]
        MW["Middleware stack<br/>RBAC · RateLimit · Security · Audit"]
        Jobs["Escalation job · Event dispatcher"]
    end

    subgraph Orchestration["🧠 Orchestration — LangGraph"]
        Supervisor["Supervisor Agent<br/>structured routing"]
        Researcher["Researcher"]
        Analyzer["Analyzer"]
        Executor["Executor"]
        Human["⏸ Human Approval<br/>interrupt_before"]
    end

    subgraph Tools["🔌 MCP Tool Server :8001 — FastMCP"]
        Search["Web search"]
        Connectors["8 connectors:<br/>HubSpot · Salesforce · Jira ·<br/>ServiceNow · GitHub · SAP ·<br/>QuickBooks · MS Graph"]
        MultiModal["PDF · Image tools"]
    end

    subgraph Data["💾 State & Memory"]
        PG["PostgreSQL 16 + pgvector<br/>checkpoints · audit · memory · tenants"]
    end

    subgraph Observe["📊 Observability"]
        Trace["LangSmith / Phoenix / Langfuse"]
        Prom["Prometheus"]
    end

    Console -->|nginx proxy /api/*| API
    API --> MW --> Supervisor
    Jobs --> Supervisor
    Supervisor -->|qualify| Researcher
    Supervisor -->|analyze| Analyzer
    Supervisor -->|propose| Executor
    Supervisor -->|await| Human
    Human -->|approve| Executor
    Researcher --> Tools
    Executor --> Tools
    Connectors --> External["External SaaS APIs"]
    Orchestration -->|checkpoint every node| PG
    Researcher -->|semantic recall| PG
    API --> Observe
    Orchestration --> Observe
```

### Data flow (the `sales_ops` happy path)

```
POST /workflows/run ─┐
                     ▼
            RBAC → RateLimit → Security → Audit middleware
                     ▼
            LangGraph compiled graph (PostgreSQL-checkpointed)
                     ▼
   QUALIFY ── Researcher ─► MCP: web_search / scrape_url (SSRF-guarded)
                     ▼
   ANALYZE ── Analyzer ──► ICP score 0–10 + risk flags
                     │  score < 4.0 ─► DISQUALIFIED
                     ▼  score ≥ 4.0
   PROPOSE ── Executor ──► draft_proposal (LLM) ─► PostgreSQL proposals
                     ▼
   APPROVE ── Human ─────► ⏸ interrupt_before → Slack card / POST /approvals/{token}/approve
                     │  rejected ─► DONE
                     ▼  approved
   EXECUTE ── Executor ──► MCP: send_email (pinned) + CRM upsert ─► mark "proposed"
                     ▼
                   DONE  (cost tracked · evaluated · audited · traced)
```

### Key design decisions

| Decision | Choice | Why |
|---|---|---|
| Orchestration | **LangGraph** | Built-in `interrupt_before`, PostgreSQL checkpointing, and streaming — production-proven |
| Tool discovery | **MCP** | Swap backends without touching agent code; a fast-growing open standard |
| Agent comms | **A2A (JSON-RPC 2.0)** | Capability-based discovery; swappable to gRPC for scale |
| Memory | **PostgreSQL + pgvector** | Co-locate semantic + transactional data; one datastore to operate |
| Evaluation | **LLM-as-judge** | Faithfulness, relevance, coherence, and hallucination in a single pass |
| Resilience | **Circuit breaker + tenacity** | Stops cascading failures at the API boundary |
| Frontend | **React 19 + Vite + nginx** | Single-origin SPA, reverse-proxied `/api/*`, hand-authored CSS with oklch tokens |

---

## 🧰 Technology Stack

| Layer | Technologies |
|---|---|
| **Orchestration** | LangGraph · LangChain Core · langgraph-checkpoint-postgres |
| **LLM providers** | OpenAI · Anthropic Claude · Ollama (local) |
| **Tools** | MCP (FastMCP, streamable-HTTP) · langchain-mcp-adapters · Tavily |
| **API** | FastAPI · Uvicorn · Pydantic v2 · pydantic-settings |
| **Data** | PostgreSQL 16 · pgvector · asyncpg · psycopg3 · Alembic |
| **Frontend** | React 19 · Vite · TanStack Router + Query · TypeScript |
| **Resilience** | tenacity · custom circuit breaker · budget guard |
| **Observability** | LangSmith · OpenTelemetry · Phoenix · Langfuse · Prometheus · tiktoken |
| **Security** | PyJWT · custom RBAC · PII / prompt / SSRF / tool-output guards |
| **Events** | Redis Streams · Kafka (aiokafka) |
| **Infra** | Docker Compose · Kubernetes · Helm · Terraform (AWS) · Fly.io |
| **Quality** | pytest · pytest-asyncio · ruff · mypy |

---

## 🚀 Quickstart

> **For a real HubSpot pipeline on Fly.io, jump to [docs/sales-ops-production.md](docs/sales-ops-production.md).** The runbook below is for local evaluation.

### Prerequisites

- **Docker** + **Docker Compose**
- **An LLM provider** — one of:
  - an OpenAI API key (default), or
  - an Anthropic API key, or
  - a local [Ollama](https://ollama.com) daemon (privacy / air-gapped mode)
- *(Optional)* a Tavily API key for real web search, and a LangSmith key for tracing
- *(Optional, for the `sales_ops` production path)* a HubSpot Private App token with the 6 CRM scopes in the [production runbook](docs/sales-ops-production.md)

### 1. Clone and configure

```bash
git clone https://github.com/JoelJohnsonThomas/forgeflow.git
cd forgeflow
cp .env.example .env
# Edit .env — at minimum set OPENAI_API_KEY, API_SECRET_KEY, POSTGRES_PASSWORD, DEV_LOGIN_PASSWORD
```

> Generate a strong secret with `openssl rand -hex 32` for `API_SECRET_KEY`. Startup fails fast without it.

### 2. Run migrations + start all services

```bash
docker compose --profile migration run --rm migrate   # apply Alembic migrations once
docker compose up                                      # start the stack
```

| Service | URL | Description |
|---|---|---|
| **React Console** | http://localhost:8501 | Landing page + 13-view operations console (nginx, proxies `/api/*`) |
| **FastAPI** | http://localhost:8000/docs | REST API + interactive OpenAPI UI |
| **MCP Server** | http://localhost:8001 | Tool server for agents |
| **PostgreSQL** | localhost:5432 | Database + pgvector |

### 3. Run the demo

```bash
# Option A — via the API
curl -X POST http://localhost:8000/workflows/run \
  -H "Content-Type: application/json" \
  -H "X-Role: sales_rep" \
  -d '{"lead_data": {"company_name": "Stripe"}, "workflow_type": "sales_ops"}'

# Option B — the demo script (auto-approves the proposal)
python scripts/run_demo.py "Stripe" approve
```

### 4. Verify

```bash
curl http://localhost:8000/health
# → {"status":"healthy","database":"connected","graph":"compiled"}
```

Then open **http://localhost:8501** and watch the run land in `/console/runs`. 🎉

<details>
<summary><b>🔒 Local-first mode (privacy / air-gapped with Ollama)</b></summary>

ForgeFlow can run entirely against a local Ollama daemon — no data leaves your machine.

```bash
pip install 'forgeflow[ollama]'
ollama pull llama3.2:3b      # worker model (fast)
ollama pull llama3.1:8b      # supervisor + judge (stronger)

echo "LLM_PROVIDER=ollama" >> .env
echo "OLLAMA_BASE_URL=http://localhost:11434" >> .env
docker compose up
```

> Note: pgvector embeddings currently call OpenAI. Fully-offline embeddings are tracked in the [roadmap](#-roadmap). Anthropic Claude is also supported: `pip install 'forgeflow[anthropic]'` and set `LLM_PROVIDER=anthropic`.

</details>

---

## ⚙️ Configuration

All configuration is environment-based and loaded through Pydantic Settings ([forgeflow/config.py](forgeflow/config.py)). Copy `.env.example` to `.env` — the key knobs:

| Variable | Default | Purpose |
|---|---|---|
| `LLM_PROVIDER` | `openai` | `openai` · `ollama` · `anthropic` |
| `OPENAI_API_KEY` | — | Required when `LLM_PROVIDER=openai` |
| `API_SECRET_KEY` | — | **Required.** Signs JWTs — generate with `openssl rand -hex 32` |
| `POSTGRES_PASSWORD` | — | **Required** by docker-compose |
| `DEV_LOGIN_ENABLED` / `DEV_LOGIN_PASSWORD` | `true` / — | Demo `/auth/login`. Set `false` in production and front with an OIDC IdP |
| `DOCS_ENABLED` | `true` | Disable `/docs` + `/redoc` in production |
| `CORS_ALLOW_ORIGINS` | `localhost:5173,8501` | Comma-separated allowlist — never `*` |
| `BUDGET_LIMIT_USD` | `5.0` | Per-workflow spend ceiling enforced by the budget guard |
| `TRACING_PROVIDER` | `langsmith` | `langsmith` · `phoenix` · `langfuse` · `none` |
| `TAVILY_API_KEY` | — | Real web search (optional) |
| `SLACK_BOT_TOKEN` | — | HITL approval cards in Slack (optional) |

> Optional extras gate heavier dependencies: `[ollama]`, `[anthropic]`, `[otel]`, `[multimodal]`, `[events]`, `[events-kafka]`. Install with e.g. `pip install 'forgeflow[otel,multimodal]'`.

---

## 📚 Usage Examples

### Run a workflow synchronously

```bash
curl -X POST http://localhost:8000/workflows/run \
  -H "Content-Type: application/json" \
  -H "X-Role: sales_rep" \
  -d '{
        "lead_data": {"company_name": "Acme Corp", "industry": "fintech"},
        "workflow_type": "sales_ops"
      }'
```

### Stream agent reasoning live (SSE)

```bash
curl -N -X POST http://localhost:8000/workflows/stream \
  -H "Content-Type: application/json" \
  -d '{"lead_data": {"company_name": "Stripe"}, "workflow_type": "sales_ops"}'
```

### Approve a paused proposal (human-in-the-loop)

```bash
# 1. See what's waiting
curl http://localhost:8000/approvals/pending

# 2. Approve (or /reject) — the workflow resumes from the checkpoint
curl -X POST http://localhost:8000/approvals/<token>/approve \
  -H "Content-Type: application/json" \
  -d '{"approver": "manager@acme.com", "comment": "Good fit, proceed"}'
```

### Dry-run a template workflow (no side effects)

```bash
curl -X POST http://localhost:8000/workflows/run \
  -H "Content-Type: application/json" \
  -d '{"lead_data": {"ticket": "Login broken"}, "workflow_type": "support_ops", "dry_run": true}'
```

### Search semantic memory

```bash
curl "http://localhost:8000/memory/search?q=enterprise%20fintech%20leads&limit=5"
```

### Validate a custom workflow template

```bash
python scripts/marketplace.py validate templates/community/my_workflow/
```

---

## 🔗 Workflows & Connectors

Connectors are real (non-mock) integrations exposed to agents as MCP tools. All are built on a single resilient base ([forgeflow/connectors/base.py](forgeflow/connectors/base.py)) that honors `Retry-After` on 429s, applies exponential backoff with jitter on 502/503/504, and distinguishes `RetryableError` from `PermanentError`. Each **degrades gracefully** when credentials are absent.

| Connector | Pairs with | Notes |
|---|---|---|
| **HubSpot** | `sales_ops` | Upsert-by-email contacts, idempotent `forgeflow_run_id` deals |
| **Salesforce** | `sales_ops` | Leads + opportunities + SOQL |
| **Jira Cloud** | `support_ops` | Issue create + transitions |
| **ServiceNow** | Incident mgmt | Table API incidents + change requests |
| **GitHub** | DevOps / PR review | Issues, PRs, releases, repo metadata |
| **SAP S/4HANA** | `finance_recon` | OData v2 + CSRF for orders + invoices |
| **QuickBooks Online** | `finance_recon` | Ledger + journal entries (OAuth 2.0) |
| **Microsoft Graph** | HITL approvals | Teams / Outlook / Calendar (Slack alternative) |

The MCP server mounts **14 tool routers** (search, CRM, email, data, Slack, + the 8 connectors above, plus multi-modal) — see [forgeflow/mcp/server/main.py](forgeflow/mcp/server/main.py).

---

## 🔐 API Reference

Interactive OpenAPI docs live at **http://localhost:8000/docs**. Core endpoints:

<details open>
<summary><b>Workflows</b></summary>

```
POST  /workflows/run               Trigger a workflow (sync)
POST  /workflows/stream            Trigger with SSE streaming
GET   /workflows/{id}              Run status + state
GET   /workflows/{id}/trace        Per-agent execution traces
```
</details>

<details>
<summary><b>Approvals · Agents · Memory</b></summary>

```
GET   /approvals/pending           Proposals awaiting review
POST  /approvals/{token}/approve   Resume (approved)
POST  /approvals/{token}/reject    Resume (rejected)

GET   /agents                      Registered A2A agents
GET   /agents/dispatch             A2A capability resolution map
GET   /agents/{id}/status          Agent health + run count
POST  /agents/{id}/message         Send an A2A message

POST  /memory/store                Store semantic memory
GET   /memory/search?q=            Cosine similarity search
DELETE /memory/{id}                Delete a memory
```
</details>

<details>
<summary><b>Metrics · Audit · Marketplace · Workspaces · Auth</b></summary>

```
GET   /metrics/                    System KPIs (total_runs, success_rate, avg_cost_usd…)
GET   /metrics/cost                Cost by agent
GET   /metrics/cost/by_workflow_type
GET   /metrics/cost/top_runs       Top N most expensive runs
GET   /metrics/cost/alerts         Budget alert state
GET   /metrics/evaluation          LLM-judge score aggregates
GET   /metrics/runs                Recent run history
GET   /metrics/prometheus          Prometheus exposition

GET   /audit/search                Filterable, paginated audit log
GET   /audit/stats                 Audit aggregates over N days

GET   /marketplace/templates       List installable templates
GET   /marketplace/templates/{name}
POST  /marketplace/templates/refresh

GET   /workspaces/                 List tenants
POST  /workspaces/                 Create a tenant
GET   /workspaces/{slug}

POST  /auth/login                  Issue a JWT (demo path, gate behind DEV_LOGIN_ENABLED)
POST  /auth/introspect             Decode + validate a JWT
POST  /auth/logout
```
</details>

**Authentication.** Requests carry a bearer JWT (`Authorization: Bearer <token>`). The middleware maps role → permissions ([forgeflow/middleware/auth.py](forgeflow/middleware/auth.py)). For local development, `/auth/login` issues a token when `DEV_LOGIN_ENABLED=true`; in production, disable it and front the API with an OIDC IdP. A legacy `X-Role` header is accepted for migration.

**Errors.** Standard HTTP semantics — `401` (no/invalid token), `403` (insufficient role), `422` (validation), `429` (rate-limited), `5xx` (upstream/LLM failure surfaced after retries + circuit breaker).

---

## 🛡️ Security

ForgeFlow ships a documented threat model and the controls that close each finding — see **[SECURITY_AUDIT.md](SECURITY_AUDIT.md)**.

**Built-in controls**

- **Prompt-injection guard** scores inbound text; **tool-output guard** wraps every tool result in an `<UNTRUSTED_TOOL_OUTPUT>` envelope to blunt 2nd-order injection.
- **SSRF guard** rejects private IPs, cloud metadata (IMDS), and non-http(s) schemes on every agent-controlled URL.
- **PII redactor** scrubs common identifiers (conservative — prefers over-redaction).
- **Outbound-email allowlist** pins recipients so the LLM can't choose where mail goes.
- **JWT + RBAC**, an **immutable partitioned audit log**, **rate limiting**, and a strict **CORS allowlist** (never `*`).

**Best practices**

- Set a strong `API_SECRET_KEY` (`openssl rand -hex 32`); never commit `.env`.
- Set `DEV_LOGIN_ENABLED=false` and `DOCS_ENABLED=false` in production.
- Use a secrets manager (AWS Parameter Store, GCP Secret Manager, Vault) — `.env` is for local only.
- The SPA authenticates per-user via `/auth/login`; nginx no longer injects a shared admin secret.

**Reporting a vulnerability.** Please **do not** open a public issue for security reports. Email the maintainer or use GitHub's private security advisory flow; see [SECURITY_AUDIT.md](SECURITY_AUDIT.md) for the disclosure process.

---

## ⚡ Performance & Scalability

| Concern | Approach |
|---|---|
| **Horizontal scaling** | The API is stateless — workers share one PostgreSQL checkpointer, so any worker resumes any `thread_id`. Scale with `docker compose up --scale api=4` or a Kubernetes HPA (api 2→10, mcp 1→5). |
| **Memory at scale** | `ivfflat` cosine index works well for <1M vectors; switch to **HNSW** for higher recall at scale. |
| **MCP transport** | Defaults to `streamable-http`; co-located deployments can use `stdio` for lower latency. |
| **Cost control** | `BudgetGuard` blocks an LLM call before projected spend exceeds `BUDGET_LIMIT_USD`; cost is tracked per token, per agent, per workflow. |
| **Resilience** | Circuit breaker + tenacity retries isolate flaky upstreams; `Retry-After` honored on 429s. |
| **Resource baseline** | A full local stack (Postgres + MCP + API + frontend) runs comfortably on ~4 GB RAM / 2 vCPU for evaluation. |

### Evaluation results (simulation)

| Metric | Score | Notes |
|---|---|---|
| Faithfulness | 0.91 | Outputs grounded in research context |
| Relevance | 0.88 | Proposals matched to company-specific signals |
| Coherence | 0.93 | Well-structured, internally consistent |
| Hallucination rate | 3.2% | Invented specifics caught by the judge |
| Avg cost / run | $0.042 | `gpt-4o-mini` workers, `gpt-4o` supervisor |
| Avg latency | 12.4s | Full qualify → propose pipeline |
| Qualification accuracy | 91% | vs. a 20-example manually-labeled set |

> Scores generated by an LLM judge on 20 synthetic test cases — illustrative, not a benchmark.

---

## 🚢 Deployment

| Target | Where | Notes |
|---|---|---|
| **Docker Compose** | [docker-compose.yml](docker-compose.yml) · [docker-compose.prod.yml](docker-compose.prod.yml) | Local + single-host production |
| **Kubernetes** | [k8s/](k8s/) | StatefulSet + Deployments + HPAs + NetworkPolicies + Ingress |
| **Helm** | [helm/forgeflow/](helm/forgeflow/) | Templated chart with an Alembic pre-upgrade hook |
| **Terraform (AWS)** | [terraform/aws/](terraform/aws/) | VPC + EKS + RDS PG16 (pgvector) + Secrets Manager + ECR + IRSA |
| **Fly.io** | [fly/](fly/) · [scripts/deploy_fly.sh](scripts/deploy_fly.sh) | 3 apps + managed Postgres + 6PN networking |
| **Air-gapped** | [docs/deployment/AIRGAPPED.md](docs/deployment/AIRGAPPED.md) · [scripts/build_offline_bundle.sh](scripts/build_offline_bundle.sh) | Offline bundle builder |

---

## 👩‍💻 Developer Guide

```bash
# Install dev dependencies
pip install -e '.[dev]'           # or: pip install -r requirements-dev.txt

# Quality gates
make lint                          # ruff + mypy
make fmt                           # ruff format
make test                          # full suite with coverage
make test-unit                     # fast unit tests only

# Start just the DB for local API dev
docker compose up postgres

# Run the API locally (hot-reload)
uvicorn forgeflow.api.main:app --reload

# Run the React console (Vite dev server, HMR, proxies /api → :8000)
cd frontend && npm install && npm run dev   # → http://localhost:5173
```

### Extension points

| Extend… | Pattern to copy | Add |
|---|---|---|
| A new **connector** | [forgeflow/connectors/github.py](forgeflow/connectors/github.py) | A `Connector` subclass + a matching MCP tool router under [forgeflow/mcp/server/tools/](forgeflow/mcp/server/tools/) |
| A new **MCP tool** | any router in [forgeflow/mcp/server/tools/](forgeflow/mcp/server/tools/) | Mount it in [forgeflow/mcp/server/main.py](forgeflow/mcp/server/main.py) |
| A new **workflow** | [forgeflow/workflows/sales_ops/](forgeflow/workflows/sales_ops/) | `models.py`, `prompts.py`, `stages.py`, `pipeline.py` + a `manifest.yaml` template |
| A new **LLM provider** | [forgeflow/models/provider.py](forgeflow/models/provider.py) | A lazy-imported branch in `get_model()` |
| A new **tracing backend** | [forgeflow/observability/tracing_provider.py](forgeflow/observability/tracing_provider.py) | A `TRACING_PROVIDER` branch |

---

## 📂 Project Structure

```
forgeflow/
├── agents/           # Supervisor, Researcher, Analyzer, Executor
├── graph/            # LangGraph StateGraph wiring + PostgreSQL checkpointer
├── state/            # Shared WorkflowState schema
├── mcp/              # FastMCP server (14 tool routers) + MCP client adapter
├── connectors/       # 8 enterprise connectors on a resilient base
├── a2a/              # A2A protocol, registry, transport, dispatcher
├── memory/           # pgvector semantic store + relational store
├── workflows/        # sales_ops · support_ops · finance_recon pipelines
├── api/              # FastAPI app, routers, schemas, dependencies
├── middleware/       # RBAC + JWT, audit, rate limiter, security
├── auth/ · rbac/     # JWT issuance + role policies
├── security/         # PII · prompt · SSRF · tool-output · email guards
├── resilience/       # Retry (tenacity), circuit breaker, budget guard
├── observability/    # Tracing providers, cost tracker, metrics, Prometheus
├── evaluation/       # LLM judge, metrics, dataset, eval runner
├── events/           # Redis Streams + Kafka consumers + dispatcher
├── jobs/             # Approval escalation background job
├── marketplace/      # File-based template registry
├── multimodal/       # PDF + image ingestion
├── telemetry/        # Opt-in anonymous usage emitter
└── notifications/    # Slack HITL cards

frontend/             # React 19 + Vite SPA (13 console views + landing + architecture)
tests/                # unit/ + integration/ (306 tests)
scripts/              # seed_db · run_demo · run_eval · validate_hubspot · deploy_fly · marketplace
alembic/              # 5 migrations (schema · pgvector · RBAC · escalation · multi-tenant)
k8s/ · helm/ · terraform/ · fly/   # Deployment targets
templates/            # Built-in + community workflow templates
docs/                 # Production runbook · air-gapped guide · images
```

---

## 🗺️ Roadmap

Phases 0–6 are shipped (full history in **[ROADMAP.md](ROADMAP.md)**). Highlights and what's next:

**✅ Shipped** — supervisor multi-agent core · PostgreSQL checkpointing · MCP tool server · A2A protocol · pgvector memory · JWT + RBAC + audit · cost tracking + budget guard · circuit breaker · LLM-as-judge evals · 8 enterprise connectors · Prometheus + OTel + Phoenix/Langfuse tracing · Slack HITL · approval escalation · event-driven mode (Redis/Kafka) · multi-modal (PDF + images) · template marketplace · React 19 console · K8s/Helm/Terraform(AWS)/Fly.io/air-gapped deploys.

**🚧 In progress / next** *(good first issues — see [ROADMAP.md](ROADMAP.md))*

- [ ] **Multi-tenant query scoping** — extend `workspace_id` filtering to all tenant-scoped endpoints (foundation + reference endpoints shipped).
- [ ] **Embeddings provider abstraction** — `get_embeddings()` factory for Ollama/Cohere/Voyage to unblock 100%-offline mode.
- [ ] **Terraform for GCP & Azure** — mirror the AWS module with GKE/Cloud SQL and AKS/Flexible Server.
- [ ] **Voice / Whisper transcription** — `transcribe_audio` MCP tool alongside the PDF/image pipeline.

---

## 🤝 Contributing

Contributions are welcome! Start with **[CONTRIBUTING.md](CONTRIBUTING.md)** and the **[Code of Conduct](CODE_OF_CONDUCT.md)**.

1. **Fork & branch** — `git checkout -b feat/your-feature` (or `fix/…`, `docs/…`).
2. **Set up** — `pip install -e '.[dev]'` and `docker compose up postgres`.
3. **Code to the standards** — keep it typed; `make lint` (ruff + mypy) and `make fmt` must pass.
4. **Test** — add tests next to the suite; `make test` must stay green (306+ and counting).
5. **Open a PR** — describe the change, link any issue, and ensure CI is green. Issues tagged `good first issue` and `help wanted` are great entry points.

See **[COMMUNITY.md](COMMUNITY.md)** for discussion channels.

---

## 📄 License

Licensed under the **[Apache License 2.0](LICENSE)**.

<div align="center">

---

**Built for the bleeding edge of agentic AI deployment.**

⭐ Star the repo if ForgeFlow helps you ship agents to production.

[Report a bug](https://github.com/JoelJohnsonThomas/forgeflow/issues) · [Request a feature](https://github.com/JoelJohnsonThomas/forgeflow/issues) · [Read the runbook](docs/sales-ops-production.md)

</div>
