# Security Policy

## Supported Versions

ForgeFlow is pre-1.0 and ships from `main`. Security fixes are applied to the
latest release and to `main`; older tagged releases are not backported.

| Version | Supported |
|---------|-----------|
| `main` (latest) | ✅ |
| `0.1.x` | ✅ |
| < `0.1.0` | ❌ |

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security reports.** Public
disclosure before a fix is available puts every deployment at risk.

Instead, report privately via one of:

1. **GitHub Private Security Advisory** (preferred) — open a draft advisory at
   <https://github.com/JoelJohnsonThomas/forgeflow/security/advisories/new>.
   This keeps the report private and lets us collaborate on a fix.
2. **Email the maintainer** — if you cannot use GitHub advisories, email the
   repository owner (see the GitHub profile of `@JoelJohnsonThomas`). Encrypt
   with the maintainer's public key if one is published.

Please include:

- A description of the vulnerability and its impact.
- Steps to reproduce (a proof-of-concept, curl commands, or a minimal repo).
- Affected version / commit and configuration (e.g. `DEV_LOGIN_ENABLED`,
  deployment target).
- Any suggested remediation.

## Response Targets

| Stage | Target |
|-------|--------|
| Acknowledgement of your report | within **3 business days** |
| Initial severity assessment | within **7 business days** |
| Fix or mitigation for Critical/High | as soon as practicable; typically **≤ 30 days** |
| Coordinated disclosure | after a fix ships, by mutual agreement |

We follow **coordinated disclosure**: we ask that you give us a reasonable
window to release a fix before any public write-up, and we will credit you in
the advisory and `CHANGELOG.md` unless you prefer to remain anonymous.

## Scope

In scope: the ForgeFlow application code (API, MCP tool server, agents,
middleware, connectors, auth), its default Docker/Kubernetes/Helm/Terraform
deployment manifests, and documented configuration.

Out of scope: vulnerabilities in third-party dependencies (report those
upstream, though we appreciate a heads-up), issues that require a
pre-compromised host, and findings that only apply when documented security
guidance is ignored (e.g. running with `DEV_LOGIN_ENABLED=true`, a default
`API_SECRET_KEY`, or `DOCS_ENABLED=true` in production — see the hardening
checklist below).

## Hardening Checklist (operators)

Before exposing ForgeFlow to untrusted traffic:

- Set a strong `API_SECRET_KEY` (`openssl rand -hex 32`) — never a default.
- Set `DEV_LOGIN_ENABLED=false` and front the API with an OIDC IdP
  (`/auth/oidc/exchange`).
- Set `DOCS_ENABLED=false`.
- Use an explicit `CORS_ALLOW_ORIGINS` allowlist — never `*`.
- Set `TRUSTED_PROXY_COUNT` to your real reverse-proxy hop count.
- Load secrets from a manager (AWS Parameter Store, GCP Secret Manager, Vault);
  `.env` is for local development only and is git-ignored.
- Rotate any credential that has ever appeared in a `.env` on a shared machine.

The application validates these at startup and **refuses to boot** in a
production-shaped configuration when they are unsafe (see
`Settings.validate_runtime()` in `forgeflow/config.py`).

## Threat Model

The full threat model, attacker scenarios, and the status of each historical
finding are tracked in [SECURITY_AUDIT.md](SECURITY_AUDIT.md).
