# ForgeFlow Roadmap

This document tracks the multi-phase plan for turning ForgeFlow into a production-ready open-source toolkit for multi-agent enterprise workflows.

---

## Phase 0 — Foundation _(shipped)_

The initial build (commits `9f035bb` through `e70ee90`):
- LangGraph hub-and-spoke supervisor with PostgreSQL checkpointing
- MCP server (FastMCP) with web search, CRM, email, data tools
- A2A protocol skeleton (AgentCard, A2ATask, A2AArtifact, registry, transport)
- PostgreSQL + pgvector memory layer
- FastAPI control plane with RBAC + audit + rate-limit middleware
- Streamlit dashboard (overview / traces / cost / evaluation pages)
- Evaluation framework (LLM-as-judge, faithfulness, hallucination flagging)
- Full CI/CD pipeline (lint + test + Docker build to GHCR)
- Docker compose for dev and prod profiles

---

## Phase 1 — OSS Expansion _(shipped)_

Closed the gap between "architectural scaffolding exists" and "production-useful tool".

| Track | Status | Description |
|-------|--------|-------------|
| **A** Cost tracking wiring | _shipped_ | `CostTracker` + `BudgetGuard` now run in every worker node; `total_cost_usd` reflects real spend |
| **B** OSS basics | _shipped_ | LICENSE (Apache 2.0), CONTRIBUTING, CODE_OF_CONDUCT, ROADMAP, issue/PR templates |
| **C** Security middleware | _shipped_ | PII redactor + prompt-injection guard at the API boundary |
| **D** Multi-domain workflows | _shipped_ | `support_ops` and `finance_recon` templates alongside `sales_ops` |
| **E** Real Slack connector | _shipped_ | HITL approvals post a Slack card with approve/reject deep-link buttons |
| **F** Model-provider abstraction | _shipped_ | OpenAI (default), Ollama (local), Anthropic — switch via `LLM_PROVIDER` |

---

## Phase 2 — Observability & Governance _(shipped)_

| Item | Status | Rationale |
|------|--------|-----------|
| Prometheus + OpenTelemetry export | _shipped_ | `/metrics/prometheus` endpoint + OTel FastAPI instrumentor; vendor-neutral via OTLP |
| Phoenix / Langfuse integration | _shipped_ | `TRACING_PROVIDER` switch auto-configures OTel endpoint + auth per backend |
| Evaluation suite in CI | _shipped_ | `.github/workflows/eval.yml` runs the eval suite + regression check against a baseline JSON |
| Cost dashboard improvements | _shipped_ | Per-workflow-type breakdown, budget alert banner, top-cost drill-down |
| Audit log search UI | _shipped_ | `/audit/search` + dashboard page 5 for compliance queries |

## Phase 3 — Enterprise Features

| Item | Rationale |
|------|-----------|
| JWT authentication | Replace dev-only `X-User-Id` / `X-Role` headers |
| Multi-tenant isolation | Per-workspace state, secrets, RBAC scopes |
| A2A in-workflow dispatch | Agents calling `registry.discover()` for true cross-process orchestration |
| Workflow simulation / dry-run | "What if" mode that runs without external side effects |
| Approval escalation rules | Auto-escalate stale approvals to a manager after timeout |

## Phase 4 — Connector Library

Real (non-mock) integrations via MCP tools. Each is a separate issue.

| Connector | Use case |
|-----------|----------|
| Salesforce | Lead and opportunity sync |
| HubSpot | Marketing contact and pipeline sync |
| Jira | Ticket creation from support workflows |
| ServiceNow | Incident management |
| SAP S/4HANA | ERP order and invoice operations |
| QuickBooks | SMB finance reconciliation |
| Microsoft Graph (Teams, Outlook) | Notifications and email drafting |
| GitHub | Repo operations and PR review automation |

## Phase 5 — Deployment & Platform

| Item | Rationale |
|------|-----------|
| Kubernetes manifests + Helm chart | Standard enterprise deployment target |
| Terraform module (AWS / GCP / Azure) | Infrastructure-as-code for cloud teams |
| Air-gapped deployment guide | Privacy-sensitive industries (healthcare, finance, government) |
| Horizontal autoscaling | API and MCP server scaling under load |

## Phase 6 — Community & Ecosystem

| Item | Rationale |
|------|-----------|
| Agent / template marketplace | Discoverability of community-contributed workflows |
| Multi-modal input (PDF, images, voice) | Document-heavy enterprise workflows |
| Event-driven mode (Kafka, Redis Streams) | Real-time pipelines vs. request/response |
| Discord + GitHub Discussions | Community Q&A and showcase space |
| Anonymous usage telemetry (opt-in) | Adoption signals to guide roadmap |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Issues tagged `help wanted` and `good first issue` are open for community pickup. To propose a roadmap addition, open a GitHub issue using the **Feature Request** template.
