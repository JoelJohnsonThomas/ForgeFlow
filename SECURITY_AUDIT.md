# ForgeFlow — Pre-Production Security Audit

**Audited commit:** `46c4852` on `main`
**Auditor role:** principal security engineer + offensive red-team
**Scope:** entire repo (backend, frontend, MCP tool server, A2A protocol, agents, infra IaC, CI/CD)
**Verdict (TL;DR):** ForgeFlow is a well-architected MVP with thoughtful primitives (middleware stack, RBAC, audit log, PII redactor, prompt guard, network policies, IRSA) but in its current state is **not safe for untrusted multi-tenant traffic**. Several **critical** authentication/authorization holes are reachable in under 60 seconds, and indirect prompt injection through MCP tool outputs is not addressed by the existing PromptGuard.

---

## Action Tracking

This file tracks every finding from the audit. Each entry has a status:

- `OPEN` — not started
- `FIXED-CODE` — patched in this repo by a follow-up commit
- `EXTERNAL` — requires action outside the repository (key rotation, account signup, infra provisioning)
- `WONTFIX` — accepted risk with stated mitigation

See the matching commit(s) referenced in the **Status** field for the exact change.

---

## 1. Executive Summary

| Dimension | Maturity | Notes |
|---|---|---|
| Identity & Auth | 2 / 10 | `/auth/login` mints admin tokens with no password; API secret doubles as wildcard admin bearer; nginx hard-codes that secret for every browser request. |
| Multi-tenant isolation | 2 / 10 | `workspace_id` columns NULLable; users self-assign workspace at login; several queries do not filter by tenant. |
| Network / infra | 6 / 10 | Solid K8s baseline (NetPol, runAsNonRoot, IRSA, ECR scan-on-push). Ingress TLS commented out, namespaceSelector `{}` too permissive, `:latest` collides with `IMMUTABLE` ECR policy. |
| AI / agent safety | 3 / 10 | PromptGuard scans only inbound HTTP bodies, not tool outputs. `scrape_url`, `email_send_email`, `query_db` are textbook SSRF / exfil / SQLi vectors. |
| Secrets hygiene | 4 / 10 | Good Terraform → Secrets Manager → ESO path. Live API key in `.env`, weak defaults baked into compose, JWT secret reused as service token. |
| Supply chain | 5 / 10 | No SBOM, no Trivy/Grype gate, no Cosign signing, no dependency-review action, `requirements.txt` only pins minimums. |
| Observability | 7 / 10 | Audit log, Prometheus, OTel, LangSmith — good. Audit writes are best-effort and swallow exceptions. |
| **Overall security score** | **38 / 100** | Acceptable for OSS preview, **blocking for SaaS GA**. |

Target after this audit's fixes: **80+**.

---

## 2. Critical Risks

### C-1 — `.env` on disk holds a live `sk-proj-...` OpenAI key
- **Risk:** Critical · **CVSS:** 9.1
- **Where:** `.env` line 11 (working tree only; verified not in `git ls-files`).
- **Attack:** Filesystem access (lost laptop, snapshot, IDE plugin telemetry, accidental `git add -f`) → free OpenAI quota on the project's account.
- **Status:** `EXTERNAL` — Anthropic-side tool cannot rotate the key.
- **Manual fix required:**
  1. Revoke the key at <https://platform.openai.com/api-keys>.
  2. Issue a new project-scoped key with a monthly spend cap.
  3. Replace the contents of `.env` (which is `.gitignore`d).
  4. Install a `pre-commit` hook with `gitleaks` to block future leakage.

### C-2 — Nginx grants every browser user the admin service token
- **Risk:** Critical · **CVSS:** 9.8
- **Where:** `frontend/nginx.conf.template:27` (`proxy_set_header Authorization "Bearer ${API_SECRET_KEY}"`) combined with `forgeflow/middleware/auth.py:104-107` (treats that secret as `role=admin`).
- **Attack:** Anyone reaching the SPA is silently authenticated as `*:*` admin.
- **Status:** `FIXED-CODE` — nginx no longer injects the header. The SPA fetch wrapper now attaches a user JWT from `sessionStorage`.

### C-3 — `/auth/login` issues admin JWTs with no password / no IdP
- **Risk:** Critical · **CVSS:** 9.8
- **Where:** `forgeflow/api/routers/auth.py:48-70`. Whitelisted from RBAC at `forgeflow/middleware/auth.py:31`.
- **Attack:** `curl -X POST .../auth/login -d '{"user_id":"admin","role":"admin"}'` → admin token.
- **Status:** `FIXED-CODE` (partial — dev path now requires a shared dev password from env, IP-rate-limited, and the route is marked dev-only with a startup warning). Full OIDC integration is `EXTERNAL`.

### C-4 — `workspace_id` is self-asserted by the user at login
- **Risk:** Critical · **CVSS:** 8.7
- **Where:** `forgeflow/api/routers/auth.py:62` — `workspace_id=req.workspace_id` taken from the request body.
- **Attack:** Tenant-A user logs in claiming tenant-B's workspace_id and reads tenant B's data.
- **Status:** `FIXED-CODE` — login now verifies `(user_id, workspace_id) ∈ workspace_members` before issuing a JWT.

### C-5 — Indirect prompt injection bypasses every security layer
- **Risk:** Critical · **CVSS:** 9.0
- **Where:** `forgeflow/middleware/security.py:38-92` — PromptGuard scans only inbound HTTP bodies. MCP tool outputs (scraped URLs, search results, CRM data) feed straight into the LLM with no guard.
- **Attack:** Poison a public page; agent scrapes it; embedded instructions hijack the agent.
- **Status:** `FIXED-CODE` — MCP tool outputs are now wrapped in an `<UNTRUSTED_TOOL_OUTPUT name="…">` envelope and re-scanned by PromptGuard. Sanitisation lives in `forgeflow/security/tool_output_guard.py`. Side-effecting tools (`email_send_email`) take recipients from a typed allowlist, not LLM output.

### C-6 — `scrape_url` MCP tool = SSRF + cloud-credential disclosure
- **Risk:** Critical · **CVSS:** 9.6 in cloud deployments
- **Where:** `forgeflow/mcp/server/tools/search_tools.py:60-91`. Arbitrary URL, redirects followed, no scheme/host blocklist.
- **Attack:** Indirect prompt injection → `scrape_url("http://169.254.169.254/latest/meta-data/iam/security-credentials/…")` → exfil credentials via `email_send_email`.
- **Status:** `FIXED-CODE` — both `scrape_url` and `BaseConnector._request` now route through `forgeflow/security/ssrf_guard.py`, which blocks RFC-1918, loopback, link-local, IPv6 ULA/link-local, non-HTTP schemes, and re-resolves DNS after each redirect. **`EXTERNAL` follow-up:** enforce IMDSv2 (`http_tokens=required`, `http_put_response_hop_limit=1`) on every EC2/EKS node — Terraform change applied in this commit set for future cluster builds.

---

## 3. Architecture Weaknesses

| # | Issue | Status |
|---|---|---|
| A-1 | Single HS256 secret = JWT signing + service token + nginx header | `FIXED-CODE` (service-token path removed; KMS-managed RS256 keys are `EXTERNAL` follow-up) |
| A-2 | Middleware order: rate limiter runs before RBAC, keyed on `"anonymous"` | `FIXED-CODE` (reordered; anon requests now rate-limited per client IP) |
| A-3 | A2A `HTTPTransport` has no auth, no signing, no replay protection | `FIXED-CODE` (HMAC + timestamp + nonce added; receiver verifies) |
| A-4 | In-memory rate limiter does not scale across replicas | `WONTFIX` for now (documented); Redis-backed limiter is `EXTERNAL` infra add |
| A-5 | Approval token = sole authz for resume | `FIXED-CODE` (token + per-approval HMAC required; bound to `manager_user_id` + `expires_at`) |
| A-6 | Slack approval buttons leak token in URLs | `FIXED-CODE` (buttons now POST to `/slack/interactions` with Slack signing secret) — **and** the deep-link URL no longer embeds the token |

---

## 4. Backend Security Review (OWASP API Top 10)

| OWASP API risk | Before | Status |
|---|---|---|
| API1 BOLA | `GET /workflows/{id}/trace` ignored `workspace_id` | `FIXED-CODE` |
| API2 Broken Auth | C-3 + dev fallback headers + no `aud/iss/nbf/jti` | `FIXED-CODE` |
| API3 Mass assignment | `WorkflowRunRequest.lead_data: dict` passed-through | `FIXED-CODE` (every input model now `extra='forbid'`) |
| API4 Resource consumption | No per-user/workspace daily cap; SSE stream pinned uvicorn workers | `FIXED-CODE` (per-tenant daily $ + token cap; SSE keepalive cap) |
| API5 BFLA | RBAC prefix match missed `/agents/*/message`, `/marketplace/refresh`, `/workflows/*/trace`, `DELETE /memory/{id}` | `FIXED-CODE` (route map extended; unmapped = deny) |
| API6 Sensitive business flow | No CAPTCHA / device check on `/workflows/run` | `WONTFIX` (per-tenant cost cap is the substitute; CAPTCHA is `EXTERNAL`) |
| API7 SSRF | C-6 + connector base | `FIXED-CODE` |
| API8 Misconfig | `allow_origins=["*"]`; no CSP/HSTS/XFO/Referrer; `/docs` public | `FIXED-CODE` (CORS allowlist via env; security headers in nginx; `/docs` admin-only via env flag) |
| API9 Inventory mgmt | No `/api/v1` versioning | `WONTFIX` (tracked separately) |
| API10 Unsafe consumption | Third-party tool responses straight into LLM | `FIXED-CODE` (C-5) |

---

## 5. Frontend Security Review

- **No `dangerouslySetInnerHTML`** — verified via grep. Good.
- **Auth token storage:** post-C-2, the SPA stores the user JWT in `sessionStorage` (cleared on tab close, not readable by other tabs/origins). When you adopt cookie-based sessions, switch to `HttpOnly; Secure; SameSite=Strict` + CSRF double-submit.
- **Security headers** added in `frontend/nginx.conf.template`:
  - `Content-Security-Policy` (default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; connect-src 'self'; img-src 'self' data:; object-src 'none'; frame-ancestors 'none'; base-uri 'self')
  - `Strict-Transport-Security: max-age=63072000; includeSubDomains; preload`
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `Permissions-Policy: camera=(), microphone=(), geolocation=()`
- **CSRF:** N/A today (Bearer header, no cookies). Revisit if you adopt cookie sessions.

---

## 6. Database Security Review

| Finding | Status |
|---|---|
| Postgres password defaults to `forgeflow:forgeflow` | `FIXED-CODE` (compose now requires `POSTGRES_PASSWORD` via `:?required`) |
| No Row-Level Security | `WONTFIX` for now — documented as next-quarter work; requires app-side `SET LOCAL app.workspace_id` integration |
| `audit_log` write swallows exceptions | `FIXED-CODE` (writes go to a bounded retry queue; persistent failure triggers a metric + alert, not a silent drop) |
| `MemoryManager.recall` doesn't enforce namespace ownership | `FIXED-CODE` |
| `MemoryStoreRequest` accepts arbitrary namespace | `FIXED-CODE` (namespace must start with `workspace/{workspace_id}/`) |

---

## 7. AI Security Review

| Finding | Status |
|---|---|
| Indirect prompt injection (C-5) | `FIXED-CODE` |
| `scrape_url` SSRF (C-6) | `FIXED-CODE` |
| Executor `email_send` accepts LLM-controlled recipient | `FIXED-CODE` (recipient pinned to `lead_data.contact_email`; outbound email domains allowlisted per workspace) |
| Executor `deal_value` unbounded | `FIXED-CODE` (capped at `workspace.settings.max_deal_value_usd`, default $1M) |
| No per-tenant cost cap | `FIXED-CODE` (per-(workspace, day) USD ceiling; circuit breaker at 80%) |
| LangSmith on by default | `WONTFIX` for OSS dev; in K8s ConfigMap `LANGCHAIN_TRACING_V2=false` by default; documented |
| `MemoryManager.remember` allows RAG poisoning | `FIXED-CODE` (provenance tag `written_by_user_id`; recall excludes low-trust entries by default) |
| `pdf.py` path traversal | `FIXED-CODE` (path must resolve under `UPLOAD_DIR`) |
| PromptGuard regex trivially bypassed | `WONTFIX` (kept as noisy signal; vendor moderation is `EXTERNAL` follow-up — wire Llama Guard 3 / Lakera when budget allows) |

---

## 8. Infrastructure Security Review

| Finding | Status |
|---|---|
| Dockerfile runs as root, ships compilers | `FIXED-CODE` (multi-stage builder; runtime stage runs as `app` UID 1000, no compilers) |
| No image signing | `EXTERNAL` (cosign requires KMS key) |
| No SBOM | `FIXED-CODE` (CI generates with `anchore/sbom-action`) |
| ECR `IMMUTABLE` + K8s `:latest` collision | `FIXED-CODE` (K8s manifests pinned to `${IMAGE_TAG}` — patched by CD) |
| Ingress TLS commented out | `FIXED-CODE` (uncommented; cert-manager annotation present) |
| NetworkPolicy `namespaceSelector: {}` too permissive | `FIXED-CODE` (restricted to `kubernetes.io/metadata.name: ingress-nginx`) |
| No PSA / Kyverno enforcing baseline | `EXTERNAL` (cluster ops) |
| EKS `endpoint_public_access = true` with no CIDR restriction | `FIXED-CODE` (Terraform var `eks_public_access_cidrs` required) |
| RDS uses default CMK | `FIXED-CODE` (customer-managed KMS key provisioned in Terraform) |
| NAT GW unfiltered egress | `EXTERNAL` (requires Squid/Cilium FQDN policy) |

---

## 9. DevSecOps Review

CI additions in `.github/workflows/security.yml`:

- `bandit` — Python SAST
- `semgrep` — multi-language SAST with OWASP rules
- `pip-audit` — dependency vuln scan
- `trivy` — container image scan
- `gitleaks` — secret scan
- `checkov` — Terraform/K8s IaC scan
- `dependency-review-action` — fail PRs that introduce known-vulnerable deps
- SBOM generated with `anchore/sbom-action`

Status: `FIXED-CODE`. Cosign signing is `EXTERNAL` until KMS keys exist.

---

## 10. Authentication & Authorization Review

| Item | Status |
|---|---|
| OIDC integration (Auth0/Okta/Keycloak) | `EXTERNAL` |
| OpenFGA / Cedar policy engine | `EXTERNAL` |
| SPIFFE/SPIRE service identity | `EXTERNAL` |
| JWT `aud`/`iss`/`nbf`/`jti` | `FIXED-CODE` |
| JWT revocation list | `EXTERNAL` (Redis dep) |
| MFA / step-up on approvals | `EXTERNAL` (IdP-side) |
| Dev `/auth/login` requires shared dev password | `FIXED-CODE` |

---

## 11. Threat Model

See section 11 of the original audit (delivered in chat) for the STRIDE × component matrix. The structure stays the same; the per-cell status is now tracked through this document's `FIXED-CODE` / `EXTERNAL` markers.

---

## 12. Attack Simulations

The four end-to-end scenarios (A — drive-by admin takeover, B — cross-tenant exfil via login, C — indirect PI → IMDS theft, D — RAG poisoning) are all closed by the `FIXED-CODE` changes above. Pen-test regression coverage for them lives in `tests/security/` (created in this commit set).

---

## 13. Recommended Security Architecture (Zero-Trust)

The target architecture (WAF → OIDC sidecar → FastAPI with PolicyEngine + RLS → mTLS to MCP + A2A → egress allowlist) is documented in the chat audit, section 13. Implementation tracking:

| Layer | Status |
|---|---|
| WAF (Cloudflare / AWS WAF) | `EXTERNAL` |
| OIDC verifier sidecar (oauth2-proxy / Pomerium) | `EXTERNAL` |
| FastAPI hardening (this commit set) | `FIXED-CODE` |
| Postgres RLS | `EXTERNAL` (next quarter) |
| mTLS via SPIFFE/SPIRE | `EXTERNAL` |
| Egress proxy (Squid / Cilium FQDN) | `EXTERNAL` |

---

## 14. Production Hardening Checklist

### Critical (do not deploy without)
- [x] C-2: nginx auth-header injection removed
- [x] C-3: dev `/auth/login` requires shared password + IP rate limit
- [x] API_SECRET wildcard admin path removed
- [x] `X-User-Id`/`X-Role` legacy fallback removed
- [x] CORS tightened to env-configured allowlist
- [x] Workspace membership enforced at login
- [x] BOLA fixes: `/workflows/{id}/trace`, `/metrics/runs`, `/memory/*` scoped by workspace
- [x] RBAC route map covers every route; unmapped = deny
- [x] SSRF block in connectors + `scrape_url`
- [x] Email recipient pinned to lead-data + per-workspace allowlist
- [x] MCP tool outputs wrapped + re-scanned
- [x] Rate limiter keyed on `(workspace, user_id, route_class)` with anon IP fallback
- [x] Middleware reordered so RateLimit runs after RBAC
- [ ] **Rotate OpenAI key** (`EXTERNAL` — user action)
- [ ] **IMDSv2 enforced on EC2 nodes** (`EXTERNAL` — applies on next Terraform apply)

### High priority (within 30 days of GA)
- [ ] OIDC + SCIM via Auth0/Okta/Keycloak
- [ ] OpenFGA / Cedar for ReBAC
- [ ] Postgres Row-Level Security
- [ ] SPIFFE/SPIRE + mTLS between API ↔ MCP ↔ A2A
- [ ] Egress allowlist via Squid or Cilium FQDN
- [ ] WAF in front
- [ ] cert-manager + HSTS preload submission
- [ ] Cosign signing + Kyverno admission
- [ ] Redis-backed rate limit + per-tenant cost cap
- [ ] RS256 with KMS-backed keys; Redis `jti` revocation set
- [ ] Replace Slack URL buttons with signed Slack interactivity endpoint (done in code; needs Slack-side app config = `EXTERNAL`)
- [ ] Vendor PII solution (AWS Macie / Microsoft Presidio)

---

## 15. Final Security Score

| Sub-score | Weight | Before | After this commit set |
|---|---|---|---|
| Auth & session | 0.20 | 1/10 | 7/10 |
| AuthZ & tenant isolation | 0.15 | 2/10 | 7/10 |
| Input validation / injection | 0.10 | 5/10 | 8/10 |
| AI / agent safety | 0.10 | 3/10 | 7/10 |
| Crypto & secrets | 0.10 | 4/10 | 6/10 |
| Network / infra | 0.10 | 6/10 | 8/10 |
| Supply chain | 0.05 | 5/10 | 8/10 |
| Observability / audit | 0.10 | 7/10 | 8/10 |
| Resilience / rate limit | 0.05 | 4/10 | 6/10 |
| Compliance posture | 0.05 | 3/10 | 5/10 |
| **Weighted total** | | **38 / 100** | **~72 / 100** |

To clear **80+** you need the items in the "High priority within 30 days" list — most are infrastructure or external accounts.

---

## 16. Enterprise-Level Recommendations

(Roadmap items — none implemented in this commit set; all `EXTERNAL` or product decisions.)

1. Security-first product principle: side-effecting tools default to HITL approval per workspace.
2. Trust & Safety surface: per-workspace allowlists (recipients, MCP tools, models, daily $).
3. Compliance roadmap: SOC2 Type II + ISO 27001 + GDPR + HIPAA BAA.
4. Data residency: per-region clusters with routing tier.
5. Customer-managed keys (BYOK) for high-trust tenants.
6. Continuous red team + public bug bounty (HackerOne / Intigriti).
7. Incident response runbook + on-call rotation + notification SLA.
8. Privacy by design: per-workspace PII toggle, GDPR export/delete APIs.
9. Agent governance: version every system prompt, tool, policy; diff in admin UI.
10. Adversarial CI suite: per-role per-tenant negative tests in `tests/security/`.
