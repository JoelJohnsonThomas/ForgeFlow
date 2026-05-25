# ForgeFlow Roadmap

This document tracks the multi-phase plan for turning ForgeFlow into a production-ready open-source toolkit for multi-agent enterprise workflows.

---

## Carryover — Remaining work from Phases 3-6

Phases 0-6 are shipped. Four items are explicitly deferred — each is well-scoped, has a clear extension point, and is suitable for a focused next session or an external contribution. Good first issues for new contributors.

### 1. Multi-tenant query scoping _(from Phase 3.5)_

**Status**: Foundation shipped. Schema, JWT claim, middleware state, and the `get_workspace_id` dependency exist. **Two endpoints** are filtered by `workspace_id` (`GET /workflows/{run_id}` and `GET /audit/search`) as the reference pattern.

**Remaining**: apply the same `workspace_id` filter to every other tenant-scoped query:
- [forgeflow/api/routers/workflows.py](forgeflow/api/routers/workflows.py) — `GET /workflows` list, `GET /workflows/{id}/trace`, `POST /workflows/stream`
- [forgeflow/api/routers/approvals.py](forgeflow/api/routers/approvals.py) — `GET /approvals/pending`, `GET /approvals/{token}`, both POST endpoints
- [forgeflow/api/routers/memory.py](forgeflow/api/routers/memory.py) — `POST /memory/store`, `GET /memory/search`, `DELETE`
- [forgeflow/api/routers/metrics.py](forgeflow/api/routers/metrics.py) + [forgeflow/observability/metrics_store.py](forgeflow/observability/metrics_store.py) — every aggregate query
- [forgeflow/api/routers/audit.py](forgeflow/api/routers/audit.py) — `audit_stats` (already filters search, not stats)

**Pattern to copy**: see `search_audit_log` in [forgeflow/api/routers/audit.py](forgeflow/api/routers/audit.py) — `workspace_id = Depends(get_workspace_id)` plus a `WHERE workspace_id = $X` or `WHERE workspace_id IS NULL` branch.

**Scope**: ~12 endpoint updates + corresponding unit tests. Estimated one focused session.

### 2. Embeddings provider abstraction _(from Phase 5.4 air-gapped caveat)_

**Status**: Chat models route through `forgeflow.models.get_model()` with OpenAI / Ollama / Anthropic backends, but [forgeflow/memory/pgvector_store.py](forgeflow/memory/pgvector_store.py) **hardcodes** `OpenAIEmbeddings`. That blocks 100% offline mode — every pgvector write still calls `api.openai.com`.

**Remaining**: add an `EMBEDDINGS_PROVIDER` setting and a `get_embeddings()` factory mirroring `get_model()`:
- OpenAI (default, current behavior)
- Ollama (via `OllamaEmbeddings` — `nomic-embed-text`, `mxbai-embed-large`)
- Optional: Cohere, Voyage, locally-loaded sentence-transformers

**Pattern to copy**: [forgeflow/models/provider.py](forgeflow/models/provider.py) is the exact analogue. Lazy imports per provider with helpful `ImportError` messages.

**Scope**: ~3 files (`forgeflow/embeddings/provider.py`, settings update, pgvector_store swap) + tests. Estimated half a session.

### 3. Terraform modules — GCP and Azure _(from Phase 5.3)_

**Status**: [terraform/aws/](terraform/aws/) is the reference impl (VPC + EKS + RDS + Secrets Manager + ECR + IRSA). GCP and Azure use the same pattern with different cloud primitives.

**Remaining**:
- `terraform/gcp/` — VPC + GKE (Autopilot recommended) + Cloud SQL for Postgres (with pgvector flag) + Secret Manager + Artifact Registry + Workload Identity binding for External Secrets
- `terraform/azure/` — VNet + AKS + Azure Database for PostgreSQL Flexible Server (with `azure.extensions = vector`) + Key Vault + ACR + Azure AD Workload Identity

**Pattern to copy**: [terraform/aws/main.tf](terraform/aws/main.tf) end-to-end. Same outputs surface so the Helm chart consumes them identically.

**Scope**: each cloud is its own ~700 LOC module + README + outputs. Estimated one full session per cloud.

### 4. Voice / Whisper transcription _(from Phase 6.2 multi-modal)_

**Status**: PDF + image ingestion shipped in [forgeflow/multimodal/](forgeflow/multimodal/). Voice was deliberately deferred — it needs an audio-file pipeline and a transcription model choice.

**Remaining**: `forgeflow/multimodal/voice.py` with:
- Local path: `faster-whisper` (CTranslate2 backend, runs CPU + GPU)
- Cloud path: OpenAI Audio API (`whisper-1`) or Anthropic equivalent when available
- MCP tool `transcribe_audio(base64_bytes, mime_type, language)` mirroring `extract_pdf` / `describe_image`
- New optional extra `[voice]` with `faster-whisper` pinned

**Pattern to copy**: [forgeflow/multimodal/images.py](forgeflow/multimodal/images.py) end-to-end. Same provider lazy-load pattern.

**Scope**: 1 module + 1 MCP tool wrapper + tests. Estimated half a session.

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

## Phase 6 — Community & Ecosystem _(shipped)_

| Item | Status | Description |
|------|--------|-------------|
| Workflow template marketplace | _shipped_ | File-based registry in [templates/](templates/), `/marketplace/templates` API, dashboard page, CLI validator |
| Multi-modal input (PDF + images) | _shipped_ | [forgeflow/multimodal/](forgeflow/multimodal/) — pypdf-based text extraction + vision-LLM image description |
| Multi-modal input (voice / Whisper) | _pending_ | Deferred — needs an audio-file pipeline + transcription model in its own session |
| Event-driven mode | _shipped_ | Redis Streams + Kafka consumers in [forgeflow/events/](forgeflow/events/) feeding a shared `EventDispatcher` |
| Discord + GitHub Discussions | _shipped_ | [COMMUNITY.md](COMMUNITY.md) + discussion templates in [.github/DISCUSSION_TEMPLATE/](.github/DISCUSSION_TEMPLATE/) |
| Anonymous usage telemetry | _shipped_ | Opt-in webhook emitter in [forgeflow/telemetry/](forgeflow/telemetry/) with PII-clean allowlist |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Issues tagged `help wanted` and `good first issue` are open for community pickup. To propose a roadmap addition, open a GitHub issue using the **Feature Request** template.
