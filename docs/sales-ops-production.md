# Sales Ops — production runbook

The `sales_ops` workflow is the only ForgeFlow template currently shipped as
production-ready. This document is what a platform engineer needs to take it
from `docker compose up` to running against a real HubSpot pipeline on Fly.io
in under an hour, plus what an on-call engineer needs when something breaks at
2am.

The other two templates (`support_ops`, `finance_recon`) are scaffolds — see
[forgeflow/workflows/support_ops/pipeline.py](../forgeflow/workflows/support_ops/pipeline.py)
and [finance_recon/pipeline.py](../forgeflow/workflows/finance_recon/pipeline.py)
for the missing pieces.

---

## What "production-ready" actually means here

| Property | Implementation | Where |
|---|---|---|
| Real CRM connector | HubSpot via Private App token, upsert-by-email for contacts, search-then-PATCH for companies, `forgeflow_run_id` custom property for idempotent deals | [forgeflow/connectors/hubspot.py](../forgeflow/connectors/hubspot.py) |
| Retry-with-backoff | 429 respects `Retry-After`; 502/503/504 exponential + full jitter; max 4 attempts; permanent vs retryable errors are distinct exception classes | [forgeflow/connectors/base.py](../forgeflow/connectors/base.py) |
| Idempotency on retry | Same lead → same contact, same workflow run_id → same deal, no duplicates | [executor.py](../forgeflow/agents/executor.py) calls `hubspot_upsert_contact` + `hubspot_create_deal_idempotent` |
| Pre-flight validation | One script proves end-to-end against your real HubSpot before you commit a workflow | [scripts/validate_hubspot.py](../scripts/validate_hubspot.py) |
| Auditable history | Every `POST /workflows/run` records actor + role + IP + outcome in `audit_log` (partitioned by tenant+day) | [forgeflow/middleware/audit.py](../forgeflow/middleware/audit.py) |
| Cost cap per run | `BudgetGuard` raises before the next LLM call if projected spend > `BUDGET_LIMIT_USD` | [forgeflow/resilience/budget_guard.py](../forgeflow/resilience/budget_guard.py) |
| Resumable across pods | LangGraph PostgreSQL checkpointer; any worker can resume any `thread_id` after a restart | [forgeflow/graph/checkpointer.py](../forgeflow/graph/checkpointer.py) |
| Human-in-the-loop approval | `interrupt_before: ["human_approval"]`; workflow suspends until `POST /approvals/{token}/approve` | [forgeflow/api/routers/approvals.py](../forgeflow/api/routers/approvals.py) |

If you change the workflow and break any of the above, the validation script
(`python scripts/validate_hubspot.py`) is the first thing to re-run.

---

## Prereqs (10 min, one-time)

### 1. HubSpot Private App + custom property

1. HubSpot → **Settings → Integrations → Private Apps → Create a private app**.
2. **Scopes** (these exactly — fewer breaks the upsert path, more is dangerous):
   - `crm.objects.contacts.read`, `crm.objects.contacts.write`
   - `crm.objects.companies.read`, `crm.objects.companies.write`
   - `crm.objects.deals.read`, `crm.objects.deals.write`
3. Save → **Auth → Show token** → copy the `pat-na1-…` token.
4. **One-time:** create a custom Deal property `forgeflow_run_id`
   (Settings → Properties → Deal properties → Create → Single-line text).
   The idempotent deal flow uses it for dedup; without it, deal creation
   fails with a 400.

### 2. OpenAI

Set `OPENAI_API_KEY=sk-…` in `.env`. Default models are `gpt-4o-mini` for
workers, `gpt-4o` for the supervisor — tune in `.env` via `OPENAI_MODEL` and
`OPENAI_MODEL_STRONG`.

### 3. Local stack (optional but recommended for the validation script)

```bash
cp .env.example .env  # add OPENAI_API_KEY and HUBSPOT_ACCESS_TOKEN
docker compose --profile migration run --rm migrate
docker compose up -d
```

---

## Validate end-to-end against your HubSpot (1 min)

Before deploying anything, prove the wiring works:

```bash
export HUBSPOT_ACCESS_TOKEN=pat-na1-...
export HUBSPOT_TEST_EMAIL=qa+forgeflow@example.com
python scripts/validate_hubspot.py
```

You should see six `PASS` lines and one `ASSERT` confirming the idempotent
deal returned the same id on both calls. The most common failure is missing
the `forgeflow_run_id` custom property — the script tells you exactly what to
fix.

The script intentionally writes to your real HubSpot (a contact, a company, a
deal). Use a non-production HubSpot account, or delete the test records
afterwards — search for `qa+forgeflow@example.com` and the deal name
`ForgeFlow QA · forgeflow-validate-…`.

---

## Trigger a workflow against your data (2 min)

After the validation passes, run a real workflow end-to-end:

```bash
curl -X POST http://localhost:8000/workflows/run \
  -H "Content-Type: application/json" \
  -H "X-Role: sales_rep" \
  -d '{
    "workflow_type": "sales_ops",
    "lead_data": {
      "company_name": "Stripe",
      "contact_email": "you@yourcompany.com",
      "contact_firstname": "Test",
      "contact_lastname": "Lead",
      "domain": "stripe.com",
      "industry": "FINANCIAL_SERVICES"
    }
  }'
```

The workflow pauses at `human_approval`. Approve it:

```bash
# Get the pending approval token
curl http://localhost:8000/approvals/pending -H "X-Role: manager"

# Approve it (paste the token from above)
curl -X POST http://localhost:8000/approvals/<token>/approve \
  -H "Content-Type: application/json" \
  -H "X-Role: manager" \
  -d '{"note": "looks good"}'
```

Verify the result in HubSpot:
- Contact: search for `you@yourcompany.com` (created or updated)
- Company: search for `stripe.com` (created or updated)
- Deal: search for `Stripe — ForgeFlow proposal`; check the `forgeflow_run_id`
  property matches the workflow_id returned from `POST /workflows/run`.

Re-running the same `POST /workflows/run` with the same inputs MUST NOT
create a second contact or a second deal. If it does, file a bug.

---

## Deploy to Fly.io (15 min)

ForgeFlow ships three Fly apps: API, MCP server, console. The MCP server
talks to the API over Fly's private 6PN network (`forgeflow-mcp.internal`);
only the API and console are publicly reachable. Postgres is Fly's managed
Postgres with pgvector available via extension.

### 1. Provision

```bash
fly auth login

# Three apps
fly apps create forgeflow-api
fly apps create forgeflow-mcp
fly apps create forgeflow-console

# Managed Postgres (paid; ~$2/mo for shared-cpu-1x, 10GB)
fly postgres create --name forgeflow-pg --region iad \
    --vm-size shared-cpu-1x --volume-size 10
fly postgres attach -a forgeflow-api forgeflow-pg
# This sets DATABASE_URL on forgeflow-api.

# Enable pgvector (required for memory.recall)
fly postgres connect -a forgeflow-pg
postgres=# CREATE EXTENSION IF NOT EXISTS vector;
postgres=# \q
```

### 2. Secrets

```bash
# Generate a service-token secret used by the SPA → API auth path
SECRET=$(openssl rand -hex 32)

# API gets the AI + CRM tokens + the JWT signing key
fly secrets set -a forgeflow-api \
    OPENAI_API_KEY=sk-... \
    HUBSPOT_ACCESS_TOKEN=pat-na1-... \
    API_SECRET_KEY=$SECRET

# Convert the auto-created DATABASE_URL into the two DSN forms forgeflow needs.
# (Fly's postgres attach sets DATABASE_URL=postgres://user:pass@host:port/db.)
DB=$(fly ssh console -a forgeflow-api -C "printenv DATABASE_URL" | tr -d '\r')
DB_BODY=${DB#postgres://}
fly secrets set -a forgeflow-api \
    POSTGRES_URL=postgresql+asyncpg://$DB_BODY \
    POSTGRES_SYNC_URL=postgresql+psycopg://$DB_BODY

# MCP gets the same CRM token (so the tool wrappers can call HubSpot)
fly secrets set -a forgeflow-mcp \
    OPENAI_API_KEY=sk-... \
    HUBSPOT_ACCESS_TOKEN=pat-na1-...

# Console nginx injects the service token on /api/* — same SECRET as the API
fly secrets set -a forgeflow-console API_SECRET_KEY=$SECRET
```

### 3. Deploy

```bash
bash scripts/deploy_fly.sh
```

The script deploys MCP → API (with `alembic upgrade head` as the release
command) → console. Each `fly deploy` exits with a green ✓ when its health
check passes.

### 4. Smoke test

```bash
curl https://forgeflow-api.fly.dev/health
# {"status":"healthy","database":"connected","graph":"compiled"}

# The console URL — open in a browser
fly info -a forgeflow-console --json | jq -r '.Hostname'
```

### 5. Custom domain + TLS (optional, 5 min)

```bash
fly certs add -a forgeflow-console console.yourdomain.com
# Then add a CNAME at your DNS provider per the instructions Fly prints.
```

---

## On-call runbook

### "I deployed a change and now nothing works"

```bash
fly logs -a forgeflow-api --instance latest | tail -200
fly logs -a forgeflow-mcp --instance latest | tail -100
```

Rollback fast:

```bash
fly releases -a forgeflow-api          # list release IDs
fly deploy -a forgeflow-api --image registry.fly.io/forgeflow-api:v<N-1>
```

### "Workflow is stuck at `awaiting_approval`"

Check the approval table:

```bash
curl https://forgeflow-api.fly.dev/approvals/pending \
  -H "Authorization: Bearer $API_SECRET_KEY"
```

If no row appears, the approval write failed at workflow time — check the API
logs for `Audit log write failed` (rare since the codec fix in
[forgeflow/database.py](../forgeflow/database.py)). Resume manually if
necessary:

```bash
curl -X POST https://forgeflow-api.fly.dev/approvals/<token>/reject \
  -H "Authorization: Bearer $API_SECRET_KEY" \
  -d '{"note":"manual close — see incident #..."}'
```

### "HubSpot returning 429 and burning retries"

The backoff is automatic but you've likely hit a daily quota. Check current
state:

```bash
curl -H "Authorization: Bearer $HUBSPOT_ACCESS_TOKEN" \
  https://api.hubapi.com/account-info/v3/api-usage/daily
```

If you're near the cap, pause the workflow queue:

```bash
fly scale count 0 -a forgeflow-api  # stop accepting new runs
# wait for the daily reset (00:00 UTC), then scale back up
fly scale count 1 -a forgeflow-api
```

In-flight workflows checkpointed mid-run will resume from the last checkpoint
when the API comes back up.

### "A duplicate contact appeared in HubSpot"

This shouldn't happen — the executor calls `hubspot_upsert_contact_by_email`,
which is idempotent on email. If it does:

1. Run the validation script: `python scripts/validate_hubspot.py`.
   The "must NOT duplicate" check will fail if the upsert path is broken.
2. Check the workflow's actual tool sequence in the trace:
   `GET /workflows/{run_id}/trace`. If you see `hubspot_create_contact` (not
   the upsert variant), an agent prompt was edited to call the non-idempotent
   tool — fix the prompt.

### "Budget guard is halting workflows"

Expected behavior — the cap exists because runaway runs are a real failure
mode. Check current spend:

```bash
curl https://forgeflow-api.fly.dev/metrics/cost/alerts \
  -H "Authorization: Bearer $API_SECRET_KEY"
```

Raise the cap (per-deployment) only if intentional:

```bash
fly secrets set -a forgeflow-api BUDGET_LIMIT_USD=50
fly deploy -a forgeflow-api  # restart picks up the new value
```

---

## Operations

### Backups

Fly's managed Postgres takes daily snapshots automatically (retained 7 days
on the shared-cpu-1x plan; configurable). Verify:

```bash
fly postgres backups -a forgeflow-pg
```

For point-in-time restore beyond the snapshot window, run logical backups via
cron from a separate host:

```bash
pg_dump $DATABASE_URL | gzip > forgeflow-$(date -u +%Y%m%dT%H%M).sql.gz
aws s3 cp forgeflow-*.sql.gz s3://your-backup-bucket/forgeflow/
```

### Secret rotation

```bash
# Rotate the API JWT-signing / SPA service-token key
NEW=$(openssl rand -hex 32)
fly secrets set -a forgeflow-api API_SECRET_KEY=$NEW
fly secrets set -a forgeflow-console API_SECRET_KEY=$NEW
# Both apps restart; in-flight SPA requests get a 401 once and re-auth.

# Rotate HubSpot token
# 1. HubSpot → Private App → Rotate token, copy new pat-na1-...
fly secrets set -a forgeflow-api  HUBSPOT_ACCESS_TOKEN=pat-na1-...
fly secrets set -a forgeflow-mcp  HUBSPOT_ACCESS_TOKEN=pat-na1-...
```

### Scaling

The API is stateless — scale horizontally; all workers share the same
PostgreSQL checkpointer:

```bash
fly scale count 4 -a forgeflow-api
```

The MCP server is also stateless and can scale similarly. Postgres scales
vertically (Fly's `fly postgres update --vm-size`) and via read replicas
(`fly postgres replica create`).

Concurrency budget is enforced per-machine via the `http_service.concurrency`
block in `fly/api.toml` (soft_limit 50, hard_limit 80). Tune based on the
slowest LLM call you've measured.

### Observability

Live console: `https://<your-console-host>/` ships with cost, run history,
approval queue, audit log, agent topology — all wired to the live API.

For Prometheus scrape: `GET /metrics/prometheus` (no auth required so your
scraper doesn't need the service token). For LangSmith traces, set
`LANGCHAIN_TRACING_V2=true` and `LANGCHAIN_API_KEY` on `forgeflow-api`.

---

## What's deliberately NOT in this runbook (yet)

- **Per-user JWT login** instead of the service-token wildcard. See the note
  in [forgeflow/middleware/auth.py](../forgeflow/middleware/auth.py); the
  backend supports it via `/auth/login`, only the SPA flow is unwired.
- **OAuth-installed HubSpot** (vs Private App). The connector's API surface
  doesn't change; only the token-load path needs to swap to a per-tenant store.
- **The other two workflow templates.** Both raise on `.run()` today; finishing
  either is a 1-3 day project per the notes in their `pipeline.py` headers.
- **Multi-region failover.** The architecture page covers the design; Fly's
  postgres replica + region pinning makes it tractable in ~half a day of work.

If you ship any of these, update this doc.
