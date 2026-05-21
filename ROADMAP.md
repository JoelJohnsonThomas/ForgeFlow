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

## Phase 3 — Enterprise Features _(shipped)_

| Item | Status | Description |
|------|--------|-------------|
| JWT authentication | _shipped_ | Bearer JWT replaces X-Role; `/auth/login` + `/auth/introspect`; legacy header fallback for migration |
| Multi-tenant isolation | _foundation shipped_ | Schema, workspaces table, JWT claim, middleware state, two sample endpoints scoped. Remaining query updates tracked as separate issue. |
| A2A in-workflow dispatch | _shipped_ | LangGraph nodes record A2A tasks via the registry; `/agents/dispatch` shows the resolution map |
| Workflow simulation / dry-run | _shipped_ | `dry_run: true` skips CRM writes, emails, Slack pings while still running the LLM plan |
| Approval escalation rules | _shipped_ | Background task ratchets stale approvals through level 1 → 2 → auto-rejected with Slack pings |

## Phase 4 — Connector Library _(shipped)_

Real (non-mock) integrations via MCP tools. All connectors built on
[`forgeflow/connectors/base.py`](forgeflow/connectors/base.py) — graceful
degradation when credentials are missing.

| Connector | Status | Pairs with |
|-----------|--------|-----------|
| GitHub | _shipped_ | DevOps / PR-review workflows |
| Jira | _shipped_ | support_ops (ticket creation + transitions) |
| HubSpot | _shipped_ | sales_ops (contacts + deals + notes) |
| Salesforce | _shipped_ | sales_ops (leads + opportunities + SOQL) |
| ServiceNow | _shipped_ | Incident management workflow |
| SAP S/4HANA | _shipped_ | ERP order + invoice operations (OData v2 + CSRF) |
| QuickBooks Online | _shipped_ | finance_recon ledger + journal entries |
| Microsoft Graph (Teams, Outlook) | _shipped_ | HITL approvals (Slack alternative) |

## Phase 5 — Deployment & Platform _(shipped)_

| Item | Status | Description |
|------|--------|-------------|
| Kubernetes manifests | _shipped_ | Plain YAML in [k8s/](k8s/) — StatefulSet + Deployments + HPAs + NetworkPolicies + Ingress |
| Helm chart | _shipped_ | Templated equivalent in [helm/forgeflow/](helm/forgeflow/) with values.yaml + alembic pre-upgrade hook |
| Terraform module (AWS) | _shipped_ | [terraform/aws/](terraform/aws/) — VPC + EKS + RDS PG16 with pgvector + Secrets Manager + ECR + IRSA |
| Terraform modules (GCP / Azure) | _pending_ | Same pattern, different provider — next session |
| Air-gapped deployment guide | _shipped_ | [docs/deployment/AIRGAPPED.md](docs/deployment/AIRGAPPED.md) + [scripts/build_offline_bundle.sh](scripts/build_offline_bundle.sh) |
| Horizontal autoscaling | _shipped_ | HPA v2 resources for api (2→10) and mcp (1→5) with CPU + memory targets and fast-up / slow-down policies |

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
