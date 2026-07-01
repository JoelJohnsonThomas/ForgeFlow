# Authentication & Authorization

How ForgeFlow authenticates callers, issues and rotates tokens, enforces MFA,
integrates with an external IdP, and maps roles to permissions.

## Token model

| Token | Type | Lifetime | Storage | Revocation |
|---|---|---|---|---|
| **Access** | Signed JWT (HS256) | `ACCESS_TOKEN_TTL_HOURS` (default 1h) | not stored (stateless) | `jti` denylist until exp |
| **Refresh** | Opaque random (48 bytes) | `REFRESH_TOKEN_TTL_DAYS` (default 30d) | SHA-256 hash only | per-token + per-family |

Access tokens carry `sub` (username), `role`, `workspace` (optional), plus
`iss`/`aud`/`iat`/`nbf`/`exp`/`jti`, all verified on decode
([`forgeflow/auth/jwt.py`](../forgeflow/auth/jwt.py)). Refresh tokens are opaque
and only their hash is stored, so a DB leak can't be replayed
([`forgeflow/auth/tokens.py`](../forgeflow/auth/tokens.py)).

> **Note:** internal JWTs use **HS256** (shared `API_SECRET_KEY`). Migrating to
> RS256 + a KMS-managed key is tracked as future hardening. External IdP tokens
> (OIDC) are verified with **RS256** against the IdP's JWKS.

## Password login (dev / local)

`POST /auth/login` (gated by `DEV_LOGIN_ENABLED`, rate-limited 5/min/IP):

1. Look up the user in `auth_users`; verify the password with **Argon2id**
   ([`forgeflow/auth/passwords.py`](../forgeflow/auth/passwords.py)).
2. If the user has MFA enabled, require and verify `mfa_code` (else
   `401 {"detail":"mfa_required"}`).
3. Verify any requested `workspace_id` against membership.
4. Issue an access + refresh pair.

The four demo users (`admin`, `manager-1`, `rep-1`, `viewer-1`) are seeded with
the `DEV_LOGIN_PASSWORD` on startup when `DEV_LOGIN_ENABLED=true`.

## Refresh rotation & reuse detection

`POST /auth/refresh` with `{ "refresh_token": "…" }`:

- Valid, unused token → marked **used**, a new token is issued in the **same
  family**, and the pair is returned.
- Replaying a **used or revoked** token → the entire family is revoked and the
  request fails `401 refresh token reuse detected`.

This bounds a stolen refresh token's blast radius to a single use (RFC 6819 /
OAuth security BCP). `POST /auth/logout` revokes the family (and denylists the
access `jti`).

```
login ──▶ (A0, R0)
R0 ─refresh─▶ (A1, R1)   R0 now "used"
R1 ─refresh─▶ (A2, R2)   R1 now "used"
R1 ─refresh─▶ 401 + family revoked   ← reuse of R1 detected; R2 also dies
```

## MFA (TOTP)

Authenticated, self-service ([`forgeflow/auth/mfa.py`](../forgeflow/auth/mfa.py)):

1. `POST /auth/mfa/enroll` → `{ secret, otpauth_uri }`. Scan the `otpauth://`
   URI in an authenticator app. The secret is staged, not yet enforced.
2. `POST /auth/mfa/verify` with `{ "code": "123456" }` → enables MFA.
3. Subsequent logins require a valid `mfa_code`.

Operator reset (lost device):
```sql
UPDATE auth_users SET mfa_enabled = false, mfa_secret = NULL WHERE username = '<user>';
```

## OIDC (production SSO)

Set `OIDC_ENABLED=true` and configure the IdP:

| Setting | Meaning |
|---|---|
| `OIDC_ISSUER` | Expected `iss` of the IdP id_token |
| `OIDC_AUDIENCE` | Expected `aud` (this app's client id) |
| `OIDC_JWKS_URL` | IdP JWKS endpoint (RS256 public keys) |
| `OIDC_DEFAULT_ROLE` | Role for auto-provisioned users (default `viewer`) |

`POST /auth/oidc/exchange` with `{ "id_token": "<idp jwt>" }` verifies the token
against the JWKS (signature + `iss`/`aud`/`exp`), provisions/looks up the user by
`sub` (JIT), and returns local access + refresh tokens
([`forgeflow/auth/oidc.py`](../forgeflow/auth/oidc.py)). Returns `404` when OIDC
is disabled.

## RBAC

The middleware ([`forgeflow/middleware/auth.py`](../forgeflow/middleware/auth.py))
verifies the bearer JWT, then checks `(method, path)` against a route→permission
map with **longest-prefix matching** and **deny-by-default** on unmapped routes.

| Role | Permissions |
|---|---|
| `admin` | `*:*` |
| `manager` | read workflows/metrics/audit/proposals, `approve:proposals`, `manage:self` |
| `sales_rep` | `execute:workflows`, read workflows/metrics, read/write memory, `manage:self` |
| `viewer` | read metrics/workflows/marketplace, `manage:self` |
| `service` | read/execute workflows, read metrics (service-to-service JWTs) |

Full matrix: [`forgeflow/rbac/policies.py`](../forgeflow/rbac/policies.py).

**Object-level authorization:** beyond role checks, `GET /workflows/{id}` and
`/trace` enforce ownership — non-elevated roles (`sales_rep`) may only read their
own runs. This closes the horizontal IDOR where one rep could read another rep's
run and agent trace.

## Production posture

- `DEV_LOGIN_ENABLED=false` — password login returns `404`; use OIDC.
- Strong `API_SECRET_KEY` (`openssl rand -hex 32`); rotating it invalidates all
  access tokens (by design).
- Put a WAF / API gateway in front for a distributed rate limiter (the built-in
  login limiter is in-process, per-replica).
- Set `TRUSTED_PROXY_COUNT` so client-IP-based limiting sees the real caller.

Startup validation refuses to boot a production-shaped config that violates
these (see [SECURITY.md](../SECURITY.md)).
