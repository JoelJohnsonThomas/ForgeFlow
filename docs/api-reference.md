# ForgeFlow API Reference

> The **always-current** source of truth is the interactive OpenAPI UI at
> **`http://localhost:8000/docs`** and the raw schema at
> **`/openapi.json`**. This document is a hand-maintained companion that adds the
> auth model, role requirements, and error semantics the raw schema doesn't
> convey. It was cross-checked against `/openapi.json`.

## Base URL & versioning

| Environment | Base URL |
|---|---|
| Local (Docker) | `http://localhost:8000` |
| Behind the console proxy | `http://localhost:8501/api` |

The API is `v0.1.0` (pre-1.0; routes may change — see [CHANGELOG.md](../CHANGELOG.md)).

## Authentication

Every route **except** the public ones below requires a bearer JWT:

```
Authorization: Bearer <access_token>
```

There is **no** header-based (`X-Role`) fallback — unauthenticated requests
fail closed with `401`. Get a token from `/auth/login` (dev) or
`/auth/oidc/exchange` (production).

**Public routes** (no token): `GET /`, `GET /health`, `GET /openapi.json`,
`/docs`, `/redoc`, `POST /auth/login`, `POST /auth/refresh`,
`POST /auth/logout`, `POST /auth/introspect`, `POST /auth/oidc/exchange`,
`GET /marketplace/templates*` (discovery is intentionally open).

### Roles & permissions

Access is role-based ([`forgeflow/rbac/policies.py`](../forgeflow/rbac/policies.py)):

| Role | Can |
|---|---|
| `admin` | everything (`*:*`) |
| `manager` | read workflows/metrics/audit/proposals, **approve** proposals, MFA self-service |
| `sales_rep` | **execute** workflows, read workflows/metrics, read/write memory, MFA self-service |
| `viewer` | read metrics/workflows/marketplace, MFA self-service |
| `service` | read/execute workflows, read metrics (service-to-service JWTs) |

Object-level rule: on `GET /workflows/{id}` and `/trace`, non-elevated roles
(e.g. `sales_rep`) may only read **their own** runs; `manager`/`admin`/`viewer`
may read any run in their workspace.

### Error semantics

| Status | Meaning |
|---|---|
| `400` | Malformed input (e.g. non-UUID path id) |
| `401` | Missing/invalid/expired token, or bad credentials |
| `403` | Authenticated but role lacks the permission |
| `404` | Resource not found **or** hidden by object-level auth |
| `409` | Conflict (e.g. approval already resolved) |
| `410` | Gone (e.g. approval expired) |
| `422` | Schema validation failure |
| `429` | Rate limited (login: 5/min/IP; global limiter otherwise) |
| `504` | Workflow exceeded `WORKFLOW_RUN_TIMEOUT_SECONDS` |
| `5xx` | Upstream/LLM failure surfaced after retries + circuit breaker |

---

## Auth

### `POST /auth/login` — password (+ optional MFA) login
Public. Gated by `DEV_LOGIN_ENABLED`. Rate limited 5/min/IP.

Request:
```json
{ "user_id": "rep-1", "password": "…", "mfa_code": "123456", "workspace_id": null, "ttl_hours": 1 }
```
`mfa_code` is required only when the user has MFA enabled (else `401 {"detail":"mfa_required"}`).

Response `200`:
```json
{ "access_token": "eyJ…", "refresh_token": "…", "token_type": "bearer",
  "expires_in": 3600, "role": "sales_rep", "workspace_id": null }
```

### `POST /auth/refresh` — rotate tokens
Public. Body `{ "refresh_token": "…" }` → new access + refresh pair. Reusing a
rotated token revokes the whole family (`401 refresh token reuse detected`).

### `POST /auth/logout`
Public. Body `{ "token": "<access>", "refresh_token": "<refresh>" }` (both optional).
Revokes the access `jti` and the refresh-token family.

### `POST /auth/introspect`
Public. Body `{ "token": "<access>" }` → `{ "active": true, "claims": {…} }` or `401`.

### `POST /auth/mfa/enroll` · `POST /auth/mfa/verify`
Authenticated (`manage:self`). Enroll returns `{ secret, otpauth_uri }`; verify
takes `{ "code": "123456" }` and enables MFA.

### `POST /auth/oidc/exchange`
Public. Requires `OIDC_ENABLED=true`. Body `{ "id_token": "<idp jwt>" }` →
verifies against the IdP JWKS and returns local tokens. `404` when OIDC is off.

---

## Workflows

| Method | Path | Role | Purpose |
|---|---|---|---|
| POST | `/workflows/run` | `execute:workflows` | Run to completion or first interrupt (sync) |
| POST | `/workflows/stream` | `execute:workflows` | Same, as an SSE event stream |
| GET | `/workflows/{run_id}` | `read:workflows` (+owner) | Run status + state |
| GET | `/workflows/{run_id}/trace` | `read:workflows` (+owner) | Per-agent traces (prompts + output) |

`POST /workflows/run` request:
```json
{ "workflow_type": "sales_ops", "lead_data": { "company_name": "Stripe" }, "dry_run": false }
```
`workflow_type` ∈ `sales_ops | support_ops | finance_recon`. `dry_run` skips
side effects (CRM writes, email, Slack) but **still calls the LLM**.
Response `200`: `{ "run_id", "thread_id", "status", "message" }`.

---

## Approvals (human-in-the-loop)

| Method | Path | Role | Purpose |
|---|---|---|---|
| GET | `/approvals/pending` | `read:proposals` | List proposals awaiting review |
| GET | `/approvals/{token}` | `read:proposals` | One approval request |
| POST | `/approvals/{token}/approve` | `approve:proposals` | Resume approved. Body `{ "note": "…" }` |
| POST | `/approvals/{token}/reject` | `approve:proposals` | Resume rejected. Body `{ "reason": "…" }` |

---

## Agents (A2A) · Memory · Metrics · Audit · Workspaces · Marketplace

| Method | Path | Role |
|---|---|---|
| GET | `/agents/` | `read:agents` |
| GET | `/agents/dispatch` | `read:agents` |
| GET | `/agents/{agent_id}/status` | `read:agents` |
| POST | `/agents/{agent_id}/message` | `send:agents` |
| POST | `/memory/store` | `write:memory` |
| GET | `/memory/search?q=&limit=` | `read:memory` |
| DELETE | `/memory/{memory_id}` | `write:memory` |
| GET | `/metrics/` · `/metrics/cost*` · `/metrics/runs` · `/metrics/evaluation` | `read:metrics` |
| GET | `/metrics/prometheus` | open (scrape endpoint; not in OpenAPI) |
| GET | `/audit/search` · `/audit/stats` | `read:audit` |
| GET | `/workspaces/` · `/workspaces/{slug}` | `read:workspaces` |
| POST | `/workspaces/` | `write:workspaces` |
| GET | `/marketplace/templates` · `/marketplace/templates/{name}` | open |
| POST | `/marketplace/templates/refresh` | `write:marketplace` |

---

## Health

`GET /health` (public) → `{ "status": "healthy", "database": "connected", "graph": "compiled" }`.
Used by container/orchestrator liveness probes.
