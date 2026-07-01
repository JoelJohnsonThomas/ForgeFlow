# Glossary

Plain-language definitions of the terms used across ForgeFlow. Each entry points
to where the concept lives in the code or the deeper docs.

## Core workflow model

**Workflow** — A compiled [LangGraph](https://langchain-ai.github.io/langgraph/)
`StateGraph` that runs a business process end to end. Each workflow is
checkpointed to PostgreSQL so it can pause and resume. See
[architecture.md](architecture.md#workflow-execution-the-sales_ops-graph).

**Workflow type (domain)** — One of `sales_ops`, `support_ops`, or
`finance_recon` (`forgeflow/workflows/`). **Only `sales_ops` is production-ready**;
`support_ops` and `finance_recon` are template scaffolds that must be run with
`dry_run: true`.

**Supervisor** — The orchestrating agent. It reads the current state and emits a
structured `RoutingDecision` (`{next, reasoning}`) to pick the next worker. It
**never calls tools directly**, which keeps control flow deterministic and
auditable.

**Worker / agent** — A specialized node the supervisor routes to. The `sales_ops`
graph has `researcher` (web search + scrape + enrich), `analyzer` (0–10 ICP score
+ risk), and `executor` (draft proposal, CRM/email side effects).

**Routing decision** — The typed object the supervisor returns each step. Because
it is structured output (not free text), the next hop is unambiguous.

**State** — The Pydantic object threaded through the graph (lead data, research
results, scores, proposal, cost, tokens). Persisted at every node.

**Checkpoint** — A saved snapshot of workflow state written to Postgres after each
node via the LangGraph Postgres checkpointer. Any API worker can resume any run
from its latest checkpoint.

**Thread / `thread_id` / `run_id`** — Identifiers for a single workflow execution.
`run_id` addresses the run in the API (`GET /workflows/{run_id}`); `thread_id`
keys the checkpoint history.

**Interrupt / human approval** — A point where the graph pauses and persists,
waiting for a person. The `sales_ops` graph interrupts before executing a
proposal; a `POST /approvals/{token}/approve` resumes it from the checkpoint.

**Dry run** — `"dry_run": true` on `POST /workflows/run`. The LLM plan still
executes, but side effects (CRM writes, email, Slack) are skipped. Required for
the scaffold workflows. **Dry runs still call the LLM and still cost money.**

## Tools & agents

**MCP** — [Model Context Protocol](https://modelcontextprotocol.io/). ForgeFlow
exposes tools over an MCP server (`forgeflow/mcp/server/`, port `8001`) so agents
call tools through a uniform interface and providers can be swapped without
touching agent code.

**MCP tool** — A single callable exposed by the MCP server (e.g.
`tavily.web_search`, `memory.recall`, `crm.stage`).

**Connector** — An adapter to an external SaaS/API (`forgeflow/connectors/`).
Eight ship today: HubSpot, Salesforce, Jira, ServiceNow, GitHub, SAP S/4HANA,
QuickBooks Online, Microsoft Graph. Connectors degrade to **mocks** when
credentials are absent, so demos and CI run offline. See
[connectors.md](connectors.md).

**A2A (Agent-to-Agent)** — A JSON-RPC 2.0 interface (`forgeflow/a2a/`) that lets
agents talk to each other directly, with `AgentCard` capability discovery and a
dispatch registry, so nodes can be deployed out of process.

**AgentCard** — The capability descriptor an agent publishes to the A2A registry.

## Memory & evaluation

**Semantic memory** — Embeddings stored in Postgres with
[pgvector](https://github.com/pgvector/pgvector), searched by cosine similarity
(`POST /memory/store`, `GET /memory/search`).

**Namespace** — A scope on a memory entry (e.g. `sales/stripe`) so one workflow
can't recall another's data.

**Evaluation / LLM-as-judge** — A harness that scores runs on faithfulness,
relevance, and coherence and reports a hallucination rate
(`GET /metrics/evaluation`).

## Reliability & cost

**Budget guard** — A per-run spend ceiling (`BUDGET_LIMIT_USD`, default `$5`). A
run halts before exceeding it.

**Circuit breaker** — Opens after `CIRCUIT_BREAKER_THRESHOLD` consecutive tool
failures to stop hammering a failing dependency.

**Execution timeout** — `WORKFLOW_RUN_TIMEOUT_SECONDS` (default `180`); a run that
exceeds it returns `504` instead of pinning a worker.

## Security & access

**RBAC** — Role-based access control enforced on every request
(`forgeflow/rbac/`, `forgeflow/middleware/auth.py`). Roles: `admin`, `manager`,
`sales_rep`, `viewer`, `service`. Deny-by-default, no header fallback. See
[auth.md](auth.md).

**OIDC** — OpenID Connect single sign-on for production
(`POST /auth/oidc/exchange`, gated by `OIDC_ENABLED`). **SAML and SCIM are not
implemented.**

**MFA** — TOTP multi-factor auth (`/auth/mfa/enroll`, `/auth/mfa/verify`), using
`pyotp`.

**Refresh-token rotation** — `POST /auth/refresh` issues a new access+refresh
pair; reusing a rotated refresh token revokes the whole family.

**Audit log** — An immutable, tenant/day-partitioned record of every request
(`GET /audit/search`, `/audit/stats`).

## Distribution

**Template** — A packaged workflow definition (`templates/community/`) with a
`manifest.yaml`. Validated with `python scripts/marketplace.py validate <file>`.

**Marketplace** — The file-based template catalog exposed at
`GET /marketplace/templates`. Browse/install UI is a **Preview** (not yet built).

## See also

- [Architecture](architecture.md) · [API reference](api-reference.md) ·
  [Configuration](configuration.md) · [FAQ](faq.md) · [Tutorials](tutorials/README.md)
