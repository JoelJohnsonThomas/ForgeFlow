# Troubleshooting

Common issues bringing ForgeFlow up locally, and how to fix them. Ordered
roughly by how often they bite new users.

## `401 Unauthorized` on every API call

**Symptom:** `{"error":"Unauthorized","detail":"missing bearer token"}` (or
`invalid token`).

**Cause:** Every non-public route requires a JWT bearer. There is **no**
`X-Role`/`X-User-Id` header fallback — those were removed.

**Fix:** Get a token first, then send `Authorization: Bearer <token>`:
```bash
TOKEN=$(curl -s localhost:8000/auth/login -H 'Content-Type: application/json' \
  -d '{"user_id":"rep-1","password":"change-me-locally-only"}' | jq -r .access_token)
curl localhost:8000/metrics/ -H "Authorization: Bearer $TOKEN"
```
See the [API reference → Authentication](api-reference.md#authentication).

## `403 Forbidden — Role '<x>' cannot <action> <resource>`

**Cause:** The token is valid but the user's role lacks the permission.
Separation of duties is enforced: `sales_rep` **executes** workflows, `manager`
**approves** them, `viewer` is read-only.

**Fix:** Use a user with the right role (`admin` has all). E.g. approvals need a
`manager-1` token; executing a run needs `rep-1` or `admin`.

## Docker daemon not running

**Symptom:** `Cannot connect to the Docker daemon` / `open //./pipe/dockerDesktopLinuxEngine`.

**Fix:** Start Docker Desktop and wait until `docker info` succeeds, then retry
`docker compose up`.

## Port 5432 already in use

**Symptom:** `Bind for 0.0.0.0:5432 failed: port is already allocated` — another
Postgres is running on the host.

**Fix:** Map ForgeFlow's DB to a different host port with a
`docker-compose.override.yml` (internal service-to-service traffic is
unaffected — it uses the compose network on 5432):
```yaml
services:
  postgres:
    ports:
      - "5433:5432"
```

## Migrations not applied / relation does not exist

**Symptom:** API logs `relation "workflow_runs" does not exist` or similar.

**Fix:** Run migrations once before (or after) starting the stack:
```bash
docker compose --profile migration run --rm migrate   # alembic upgrade head
```
If you changed a migration file after the image was built, rebuild the image
(`docker compose build api migrate`) or run Alembic from the host against the DB.

## API takes ~1–2 minutes to become healthy

**Not a bug.** On startup the API compiles three LangGraph graphs and connects
to the MCP server + Postgres checkpointer. `/health` only returns `200` after
`Application startup complete`. Poll it rather than assuming failure:
```bash
until curl -sf localhost:8000/health >/dev/null; do sleep 3; done
```

## `ModuleNotFoundError` in the API container after adding a dependency

**Cause:** The Docker image installs from **`requirements.txt`**, not
`pyproject.toml`. Adding a dep only to `pyproject.toml` won't reach the image.

**Fix:** Add the dependency to **both** `requirements.txt` and
`pyproject.toml`, then `docker compose build api`.

## `docker compose up --scale api=N` fails with a port conflict

**Cause:** The `api` service publishes a fixed host port (`8000:8000`); Docker
can't bind it N times.

**Fix:** To scale locally, remove the static port mapping and put a load
balancer / reverse proxy in front, or scale via Kubernetes (the `k8s/` HPA)
where each replica has its own address. See the Deployment section of the
README.

## `run_demo.py` crashes with `UnicodeEncodeError` on Windows

**Cause:** Windows consoles default to cp1252 and choke on the script's emoji.

**Fix:** The script now forces UTF-8 itself; if you're on an older copy, run it
with `PYTHONUTF8=1 python scripts/run_demo.py …`. The script also runs on the
**host** (not in the container) and needs `pip install -e .` plus
`DEV_LOGIN_PASSWORD` exported.

## API refuses to start in production

**Symptom:** `Refusing to start: N fatal configuration problem(s) in production`.

**Cause:** `Settings.validate_runtime()` fails closed when a prod-shaped
deployment is unsafe — default `API_SECRET_KEY`, `DEV_LOGIN_ENABLED=true`,
`CORS_ALLOW_ORIGINS='*'`, `DOCS_ENABLED=true`, or a missing LLM key.

**Fix:** Address each `CONFIG:` line in the logs. See the hardening checklist in
[SECURITY.md](../SECURITY.md).

## `429 Too many login attempts`

**Cause:** The login limiter allows 5 attempts/minute per IP.

**Fix:** Wait ~60s. Behind a proxy, set `TRUSTED_PROXY_COUNT` so the limiter
keys on the real client IP instead of the proxy.

## Locked out by MFA

If a user enabled TOTP MFA and lost the authenticator, an operator can clear it
directly:
```sql
UPDATE auth_users SET mfa_enabled = false, mfa_secret = NULL WHERE username = '<user>';
```

## LLM calls fail or cost more than expected

- **Missing key:** `OPENAI_API_KEY` (or `ANTHROPIC_API_KEY`) must be set for the
  chosen `LLM_PROVIDER`. For fully offline use, set `LLM_PROVIDER=ollama`.
- **Budget guard:** a run stops before exceeding `BUDGET_LIMIT_USD`. Raise it if
  legitimate runs are being cut off.
- **`dry_run: true` still costs money** — it skips side effects, not the LLM.

## Still stuck?

Open a discussion or issue (see [COMMUNITY.md](../COMMUNITY.md)). For anything
security-related, use the private process in [SECURITY.md](../SECURITY.md) —
**not** a public issue.
