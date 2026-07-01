# Changelog

All notable changes to ForgeFlow are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project aims to follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- **Enterprise authentication** — Argon2id password hashing, TOTP MFA
  (`/auth/mfa/enroll`, `/auth/mfa/verify`), rotating refresh tokens with reuse
  detection (`/auth/refresh`), and OIDC exchange for external IdPs
  (`/auth/oidc/exchange`). New `auth_users` / `auth_refresh_tokens` tables
  (migration `009`).
- **Security response headers** middleware — HSTS, CSP, `X-Frame-Options`,
  `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`, COOP/CORP
  on every response (`/docs` exempted from CSP).
- **Fail-fast startup config validation** — production-shaped deployments refuse
  to boot with default secrets, `DEV_LOGIN_ENABLED=true`, `CORS='*'`, missing
  LLM keys, or `DOCS_ENABLED=true` (`Settings.validate_runtime()`).
- **Execution timeout** on `POST /workflows/run` (`WORKFLOW_RUN_TIMEOUT_SECONDS`)
  so a hung LLM/tool returns `504` instead of pinning a worker.
- **Performance indexes** on `workflow_runs(user_id)` and
  `(workspace_id, status, created_at)` (migration `008`).
- **Test analytics** — TestRelic pytest reporter for the Python suite and a
  Playwright + TestRelic e2e setup for the React console.

### Changed
- `workflow_runs.user_id` and `approval_requests.resolved_by` widened from
  `UUID` to `VARCHAR` so string subjects (e.g. `rep-1`) are attributable
  (migrations `006`, `007`).
- Frontend console views are now code-split (`React.lazy`), cutting the initial
  bundle from ~547 kB to ~364 kB.

### Fixed
- **Object-level authorization (IDOR)** — `GET /workflows/{id}` and `/trace` now
  enforce ownership; non-elevated roles can no longer read another user's run or
  agent trace.
- **Approval endpoints 500** — caused by the `resolved_by` type mismatch above;
  approvals now succeed and the run completes.
- **SSRF guard crash on redirects** — `safe_get` used `httpx.URL.human_repr()`
  (nonexistent); it now serializes with `str()`, so redirect chains resolve.
- `scripts/run_demo.py` is UTF-8-safe on Windows consoles and tolerant of
  non-JSON error responses.

### Security
- Removed the shared-password-only demo login as the sole auth path; production
  now uses OIDC. See [SECURITY.md](SECURITY.md) and
  [SECURITY_AUDIT.md](SECURITY_AUDIT.md).

## [0.1.0] — 2026

Initial public release. Phases 0–6.

### Added
- Supervisor multi-agent core (researcher / analyzer / executor) on LangGraph
  `StateGraph` with PostgreSQL checkpointing.
- MCP tool server (14 tool routers) + MCP client adapter.
- Agent-to-Agent (A2A) protocol, registry, transport, and dispatcher.
- pgvector semantic memory + relational store.
- JWT + RBAC middleware, immutable partitioned audit log, rate limiting,
  strict CORS allowlist.
- Cost tracking + per-run budget guard, circuit breaker, retry-with-backoff.
- LLM-as-judge evaluation harness.
- 8 enterprise connectors (HubSpot, Salesforce, Jira, ServiceNow, GitHub,
  SAP S/4HANA, QuickBooks Online, Microsoft Graph) on a resilient base.
- Observability: Prometheus, OpenTelemetry, Phoenix/Langfuse/LangSmith tracing.
- Slack HITL approval cards + approval escalation background job.
- Event-driven mode (Redis Streams / Kafka).
- Multi-modal ingestion (PDF + images).
- File-based template marketplace.
- React 19 + Vite operations console (13 views).
- Deployment targets: Docker Compose, Kubernetes, Helm, Terraform (AWS),
  Fly.io, and an air-gapped offline bundle.
- Three workflow domains: `sales_ops` (production), `support_ops` and
  `finance_recon` (template scaffolds).

[Unreleased]: https://github.com/JoelJohnsonThomas/forgeflow/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/JoelJohnsonThomas/forgeflow/releases/tag/v0.1.0
