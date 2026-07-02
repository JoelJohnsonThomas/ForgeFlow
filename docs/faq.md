# FAQ

Short, honest answers. Where a feature isn't implemented, this page says so.

## General

**What is ForgeFlow?**
An open-source platform for running **supervisor-orchestrated multi-agent
workflows** in production — with human-in-the-loop approvals, semantic memory,
cost controls, an immutable audit log, and a live operations console. It's built
on LangGraph, FastAPI, PostgreSQL (+ pgvector), and the Model Context Protocol
(MCP).

**What version is this?**
`v0.1.0` — pre-1.0. Routes and schemas may change; see
[CHANGELOG.md](../CHANGELOG.md).

**What license?**
Apache 2.0 ([LICENSE](../LICENSE)).

**How is it different from LangGraph / CrewAI / n8n / Temporal?**
ForgeFlow *uses* LangGraph as its execution core and adds the production layer on
top: RBAC + audit, typed human approvals with escalation, per-run budget guards,
an evaluation harness, enterprise connectors over MCP, and an operations console.
It is code-first (Python), not a drag-and-drop builder — a visual graph editor is
on the roadmap, not shipped.

## Getting started

**Do I need API keys to try it?**
You need **one LLM key** (`OPENAI_API_KEY`, or `ANTHROPIC_API_KEY`, or run
[fully offline with Ollama](tutorials/02-run-offline-with-ollama.md)). Enterprise
connectors are optional — without credentials they **degrade to mocks**, so the
`sales_ops` demo runs end to end with no HubSpot/Salesforce account.

**How do I run my first workflow?**
See [Tutorial 1 — Your first workflow](tutorials/01-first-workflow.md) (~15 min).

**Is there a CLI?**
**No unified CLI yet.** ForgeFlow is driven through the **REST API**
(`http://localhost:8000`, see [api-reference.md](api-reference.md)) and Docker
Compose. There are purpose-built helper scripts in [`scripts/`](../scripts/):
`run_demo.py`, `seed_db.py`, `marketplace.py`, `run_eval.py`,
`build_offline_bundle.sh`, `deploy_fly.sh`. A packaged `forgeflow` CLI is a
candidate for a future release.

**Is there a published pip package / SDK?**
Not on PyPI. The `forgeflow` package is imported from the repo (`pip install -e .`
for host scripts). You can also call the pipeline in-process — see
[examples.md](examples.md#2-run-a-workflow-programmatically-python).

## Workflows

**Which workflows are production-ready?**
Only **`sales_ops`**. `support_ops` and `finance_recon` are **template scaffolds**
— their graphs and prompts exist, but they lack wired connectors and refuse to
run unless you pass `dry_run: true`. This is stated in the console's Workflows
view and in the [glossary](glossary.md).

**What does `dry_run` do?**
Skips side effects (CRM writes, email, Slack) but **still runs the LLM plan** —
so it still costs tokens. Use it to exercise scaffolds safely.

**Why did my run pause?**
The `sales_ops` graph **interrupts for human approval** before executing a
proposal. Approve it with a `manager` token via
`POST /approvals/{token}/approve`. See
[Tutorial 1](tutorials/01-first-workflow.md#5-approve-the-proposal).

## Auth & security

**How do I log in locally?**
Seeded demo users `rep-1` (role `sales_rep`, executes) and `manager-1` (role
`manager`, approves), password from `DEV_LOGIN_PASSWORD`. `POST /auth/login`
returns an access + refresh token pair. Dev login is gated by
`DEV_LOGIN_ENABLED` — **turn it off in production**.

**Does ForgeFlow support SSO?**
**OIDC, yes** (`POST /auth/oidc/exchange`, `OIDC_ENABLED=true`, RS256/JWKS
verification with just-in-time provisioning). **SAML and SCIM are not
implemented.** Do not assume them.

**Is MFA available?**
Yes — TOTP via `/auth/mfa/enroll` and `/auth/mfa/verify`.

**Is it SOC 2 / HIPAA certified?**
No. ForgeFlow provides security *controls* (RBAC, immutable audit log, encryption
at the database layer, GDPR-style erasure by trace ID) but carries **no
compliance certification**. See [SECURITY.md](../SECURITY.md).

## Operations

**How much does a run cost?**
It depends on the models and lead. A per-run **budget guard** (`BUDGET_LIMIT_USD`,
default `$5`) halts a run before it overspends. Track spend at `GET /metrics/cost`.

**Where's the interactive API reference?**
`http://localhost:8000/docs` (Swagger UI) and `/openapi.json`. Disable in prod
with `DOCS_ENABLED=false`. A written companion with auth/roles/errors is
[api-reference.md](api-reference.md).

**How do I deploy to production?**
Docker Compose, Kubernetes (`k8s/`), Helm (`helm/`), Terraform for AWS
(`terraform/`), or Fly.io (`fly/`, `scripts/deploy_fly.sh`). Startup validation
(`Settings.validate_runtime()`) **refuses to boot** an unsafe prod config. See the
[deployment section](../README.md#-deployment) and
[backup-dr.md](operations/backup-dr.md).

**Can I run it air-gapped?**
Yes — offline against a local Ollama daemon with a signed bundle. See
[deployment/AIRGAPPED.md](deployment/AIRGAPPED.md).

## Troubleshooting

**Everything returns `401`.** You need a bearer token — there is no header
fallback. See [troubleshooting.md](troubleshooting.md#401-unauthorized-on-every-api-call).

**`403 Forbidden`.** Your role lacks the permission (separation of duties: `rep`
executes, `manager` approves). Use the right user.

**More:** the full list is in [troubleshooting.md](troubleshooting.md).

## Still stuck?

Open a discussion or issue (see [COMMUNITY.md](../COMMUNITY.md)). For security
reports, use the private process in [SECURITY.md](../SECURITY.md) — not a public
issue.
