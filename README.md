# ⚡ ForgeFlow

> **Production-grade Multi-Agent Enterprise Workflow Orchestrator**
> Built for the bleeding edge of agentic AI deployment in 2026.

[![CI](https://github.com/JoelJohnsonThomas/forgeflow/actions/workflows/ci.yml/badge.svg)](https://github.com/JoelJohnsonThomas/forgeflow/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2.60+-green.svg)](https://langchain-ai.github.io/langgraph/)
[![MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-purple.svg)](https://modelcontextprotocol.io)
[![Docker](https://img.shields.io/badge/docker-compose-blue.svg)](https://docker.com)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

ForgeFlow orchestrates a **team of specialized AI agents** across multiple business domains — sales lead qualification, customer support triage, and finance reconciliation — all with human-in-the-loop approvals, full observability, and enterprise-grade reliability.

**Workflow templates shipped:**
- `sales_ops` — qualify → research → analyze → propose → approve → execute
- `support_ops` — triage → investigate → respond → escalate → resolve
- `finance_recon` — ingest → match → flag_variance → approve → post

Pick a workflow with `workflow_type: "..."` on `POST /workflows/run`. See [forgeflow/workflows/](forgeflow/workflows/) for each domain's prompt + state shape.

---

## Architecture

```mermaid
graph TB
    Client["Client / Dashboard"] -->|POST /workflows/run| API["FastAPI :8000"]

    API --> Graph["LangGraph StateGraph<br/>(PostgreSQL Checkpointed)"]

    Graph -->|hub-and-spoke routing| Supervisor["🧠 Supervisor Agent<br/>GPT-4o — structured routing"]

    Supervisor -->|qualify| Researcher["🔍 Researcher Agent<br/>web_search + scrape_url"]
    Supervisor -->|analyze| Analyzer["📊 Analyzer Agent<br/>0-10 scoring + risk flags"]
    Supervisor -->|propose| Executor["⚙️ Executor Agent<br/>proposal + CRM + email"]
    Supervisor -->|await approval| HumanLoop["⏸ Human Approval<br/>interrupt_before"]

    Researcher --> MCPServer["🔌 MCP Tool Server :8001<br/>FastMCP (streamable-HTTP)"]
    MCPServer --> TavilySearch["Tavily Web Search"]
    MCPServer --> CRMTools["Mock Salesforce CRM"]
    MCPServer --> EmailTools["Mock Email / SMTP"]

    Executor --> HumanLoop
    HumanLoop -->|approve| Executor
    HumanLoop -->|reject| END["✅ Done"]

    Researcher <-->|A2A messages| A2ARegistry["A2A Registry<br/>JSON-RPC 2.0"]
    Analyzer <-->|A2A messages| A2ARegistry

    Graph -->|persist every node| PostgreSQL["PostgreSQL 16<br/>+ pgvector extension"]
    Researcher -->|semantic recall| PostgreSQL
    Executor -->|structured write| PostgreSQL

    API --> Dashboard["📊 Streamlit :8501<br/>Traces • Cost • Eval"]
    Dashboard --> LangSmith["LangSmith<br/>Traces + Evals"]
```

---

## Key Design Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Orchestration | LangGraph | Built-in `interrupt_before`, PostgreSQL checkpointing, streaming — production-proven |
| Tool discovery | MCP (Model Context Protocol) | Swap backends without touching agent code; standard adopted by 150+ orgs |
| Agent communication | A2A Protocol | JSON-RPC 2.0 spec, capability-based discovery, swap to gRPC for scale |
| Memory | PostgreSQL + pgvector | Co-locate semantic + transactional data; no extra infra to manage |
| Evaluation | LLM-as-judge | Faithfulness, relevance, coherence + hallucination detection in one pass |
| Resilience | Circuit breaker + tenacity | Proven patterns that stop cascading failures at the API boundary |

---

## Quickstart

### Prerequisites
- Docker + Docker Compose
- An LLM provider — one of:
  - OpenAI API key (default)
  - A local Ollama daemon (privacy mode, see below)
  - Anthropic API key
- (Optional) Tavily API key for real web search, LangSmith key for tracing

### 1. Clone and configure

```bash
git clone https://github.com/JoelJohnsonThomas/forgeflow.git
cd forgeflow
cp .env.example .env
# Edit .env — set OPENAI_API_KEY at minimum
```

### 2. Run migrations + start all services

```bash
docker compose --profile migration run --rm migrate
docker compose up
```

Services:
| Service | URL | Description |
|---------|-----|-------------|
| FastAPI | http://localhost:8000/docs | REST API + OpenAPI UI |
| Streamlit | http://localhost:8501 | Observability dashboard |
| MCP Server | http://localhost:8001 | Tool server for agents |
| PostgreSQL | localhost:5432 | Database + pgvector |

### Local-first mode (privacy / air-gapped)

ForgeFlow can run entirely against a local [Ollama](https://ollama.com) daemon — no data leaves your machine.

```bash
# 1. Install the optional extra
pip install 'forgeflow[ollama]'

# 2. Start Ollama and pull models
ollama pull llama3.2:3b      # worker model (fast)
ollama pull llama3.1:8b      # supervisor + judge model (stronger)

# 3. Point ForgeFlow at Ollama
echo "LLM_PROVIDER=ollama" >> .env
echo "OLLAMA_BASE_URL=http://localhost:11434" >> .env

# 4. Run as usual
docker compose up
```

Anthropic Claude is also supported: `pip install 'forgeflow[anthropic]'` and set `LLM_PROVIDER=anthropic` plus `ANTHROPIC_API_KEY`.

### 3. Run the demo

```bash
# Option A: API curl
curl -X POST http://localhost:8000/workflows/run \
  -H "Content-Type: application/json" \
  -H "X-Role: sales_rep" \
  -d '{"lead_data": {"company_name": "Stripe"}, "workflow_type": "sales_ops"}'

# Option B: Demo script
python scripts/run_demo.py "Stripe" approve
```

### 4. Open the dashboard

Navigate to **http://localhost:8501** to see:
- Real-time KPIs (runs, success rate, cost)
- Agent execution Gantt chart
- Cost breakdown by agent
- LLM evaluation scores

---

## Enterprise Patterns Implemented

| Pattern | File | Description |
|---------|------|-------------|
| Supervisor multi-agent | [forgeflow/graph/builder.py](forgeflow/graph/builder.py) | Hub-and-spoke routing with LangGraph |
| PostgreSQL checkpointing | [forgeflow/graph/checkpointer.py](forgeflow/graph/checkpointer.py) | Every node persisted; any worker can resume any run |
| MCP tool server | [forgeflow/mcp/server/main.py](forgeflow/mcp/server/main.py) | FastMCP HTTP server with 8 registered tools |
| A2A agent protocol | [forgeflow/a2a/](forgeflow/a2a/) | JSON-RPC 2.0, AgentCard, capability discovery |
| PGVector semantic memory | [forgeflow/memory/pgvector_store.py](forgeflow/memory/pgvector_store.py) | ivfflat cosine index, namespace-scoped |
| Human-in-the-loop | [forgeflow/api/routers/approvals.py](forgeflow/api/routers/approvals.py) | `interrupt_before` + webhook resume |
| LLM evaluation | [forgeflow/evaluation/judge.py](forgeflow/evaluation/judge.py) | GPT-4o as judge: faithfulness, relevance, hallucination |
| Cost tracking | [forgeflow/observability/cost_tracker.py](forgeflow/observability/cost_tracker.py) | tiktoken, model cost table, per-agent breakdown |
| Circuit breaker | [forgeflow/resilience/circuit_breaker.py](forgeflow/resilience/circuit_breaker.py) | CLOSED/OPEN/HALF_OPEN state machine |
| Budget guard | [forgeflow/resilience/budget_guard.py](forgeflow/resilience/budget_guard.py) | Halts workflow before exceeding $limit |
| Simulated RBAC | [forgeflow/rbac/](forgeflow/rbac/) | Role → permission policies, middleware enforcement |
| Immutable audit log | [forgeflow/middleware/audit.py](forgeflow/middleware/audit.py) | Partitioned table, every request logged |
| SSE streaming | [forgeflow/api/routers/workflows.py](forgeflow/api/routers/workflows.py) | `astream()` + FastAPI `StreamingResponse` |

---

## API Reference

```
POST  /workflows/run            Trigger a new workflow (sync)
POST  /workflows/stream         Trigger with SSE streaming
GET   /workflows/{id}           Get run status + state
GET   /workflows/{id}/trace     Per-agent execution traces

GET   /approvals/pending        List proposals awaiting review
POST  /approvals/{token}/approve  Resume workflow (approved)
POST  /approvals/{token}/reject   Resume workflow (rejected)

GET   /agents                   List registered A2A agents
GET   /agents/{id}/status       Agent health + run count

POST  /memory/store             Store semantic memory
GET   /memory/search?q=         Cosine similarity search

GET   /metrics                  System-wide KPIs
GET   /metrics/cost             Cost by agent + day
GET   /metrics/evaluation       LLM judge score aggregates
GET   /metrics/runs             Recent run history
```

---

## Sales Ops Workflow — Stage Map

```
Input: company_name (+ optional contact, industry, budget)
  │
  ▼
QUALIFY ─── Researcher ──► web_search("{company} funding employees revenue")
  │                         scrape_url, fetch_enrichment
  ▼
ANALYZE ─── Analyzer ───► ICP scoring (0-10), risk flags, recommended_action
  │
  ├── score < 4.0 ──► DISQUALIFIED (done)
  │
  └── score ≥ 4.0 ──►
  │
PROPOSE ─── Executor ───► draft_proposal (LLM) → PostgreSQL proposals table
  │
  ▼
APPROVE ─── Human ──────► POST /approvals/{token}/approve  (manager reviews)
  │
  ├── rejected ──► DONE
  │
  └── approved ──►
  │
EXECUTE ─── Executor ───► send_email + update_lead (CRM) + mark "proposed"
  │
  ▼
DONE
```

---

## Evaluation Results (Simulation)

| Metric | Score | Notes |
|--------|-------|-------|
| Faithfulness | 0.91 | Agent outputs grounded in research context |
| Relevance | 0.88 | Proposals matched to company-specific signals |
| Coherence | 0.93 | Well-structured, internally consistent |
| Hallucination Rate | 3.2% | Invented specifics caught by judge |
| Avg Cost / Run | $0.042 | gpt-4o-mini for workers, gpt-4o for supervisor |
| Avg Latency | 12.4s | Full qualify → propose pipeline |
| Qualification Accuracy | 91% | vs. manually-labeled eval dataset (20 examples) |

> Scores generated by GPT-4o-mini acting as evaluator on 20 synthetic test cases.

---

## Project Structure

```
forgeflow/
├── agents/           # Supervisor, Researcher, Analyzer, Executor
├── graph/            # LangGraph StateGraph wiring + checkpointer
├── mcp/              # FastMCP server + langchain-mcp-adapters client
├── a2a/              # A2A protocol models, registry, transport
├── memory/           # PGVector semantic store + relational store
├── workflows/        # Sales ops pipeline, stages, prompts, models
├── api/              # FastAPI app, routers, schemas, dependencies
├── middleware/        # RBAC, audit log, rate limiter
├── rbac/             # Role policies + enforcer
├── observability/    # LangSmith tracer, cost tracker, metrics store
├── resilience/       # Retry (tenacity), circuit breaker, budget guard
└── evaluation/       # LLM judge, metrics, dataset, eval runner

dashboard/            # Streamlit 4-page observability dashboard
tests/                # unit/ + integration/
scripts/              # seed_db, run_demo, generate_eval_dataset
alembic/              # 3 database migrations (schema + pgvector + RBAC)
```

---

## Production Considerations

**Horizontal scaling**: The API is stateless — multiple workers share the same PostgreSQL checkpointer, so any worker can resume any `thread_id`. Scale with `docker compose scale api=4`.

**MCP transport**: Currently uses `streamable-http`. For co-located deployments, switch to `stdio` for lower latency. For multi-host, the same server scales independently.

**Memory at scale**: ivfflat index works well for <1M vectors. For higher recall at scale, switch to HNSW (`CREATE INDEX ... USING hnsw`).

**Secrets**: `.env` for local. Use AWS Parameter Store, GCP Secret Manager, or Vault in production. Never commit `.env`.

**Cost control**: `BudgetGuard` raises before each LLM call if projected spend exceeds `BUDGET_LIMIT_USD`. Set per-workflow or globally.

**Tracing**: Set `LANGCHAIN_TRACING_V2=true` + `LANGCHAIN_API_KEY` for automatic LangSmith traces of every agent invocation, tool call, and retry.

---

## Why This Matters for FDE Roles

Building ForgeFlow demonstrates five capabilities that distinguish senior forward-deployed engineers:

1. **Systems thinking**: The agent graph, MCP tool layer, and A2A protocol are independently swappable. A customer who uses ServiceNow can plug in a ServiceNow MCP server without changing any agent code.

2. **Production readiness**: Migrations, RBAC, immutable audit log, circuit breakers, budget guards, retry logic — not just "it works in a notebook."

3. **Protocol fluency**: MCP (Anthropic/2024), A2A (Google/2025), PostgresSaver wire protocol — showing you track the ecosystem, not just use it.

4. **Evaluation rigor**: LLM-as-judge with quantified metrics on a labeled dataset. "The agent performs well" becomes "faithfulness 0.91, hallucination rate 3.2%."

5. **Observability discipline**: Every run is traced, costed, and queryable. A customer's ops team can answer "why did run X fail and what did it cost?" without digging through logs.

---

## Local Development

```bash
# Install deps
pip install -r requirements-dev.txt

# Run tests
make test

# Lint + type check
make lint

# Start just the DB for local API dev
docker compose up postgres

# Run API locally (hot-reload)
uvicorn forgeflow.api.main:app --reload

# Run dashboard locally
streamlit run dashboard/app.py
```

---

## License

MIT © 2026 — Built as a portfolio project demonstrating enterprise agentic AI deployment.
