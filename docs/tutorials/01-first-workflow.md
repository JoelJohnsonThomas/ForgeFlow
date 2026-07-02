# Tutorial 1 — Your first workflow

**Goal:** boot ForgeFlow locally and run the production `sales_ops` workflow end
to end — trigger it as a sales rep, watch it pause for approval, approve it as a
manager, and see the result in the console.

**Time:** ~15 minutes.

## Prerequisites

- Docker Desktop running (`docker info` succeeds).
- `jq` installed (for reading JSON in the shell) — optional but handy.
- An `OPENAI_API_KEY`. (Prefer no external LLM? Do
  [Tutorial 2 — Ollama](02-run-offline-with-ollama.md) instead, then come back.)

## 1. Configure

```bash
git clone https://github.com/JoelJohnsonThomas/forgeflow
cd forgeflow
cp .env.example .env
```

Open `.env` and set at least:

```bash
OPENAI_API_KEY=sk-...              # your key
API_SECRET_KEY=$(openssl rand -hex 32)   # signs JWTs
DEV_LOGIN_PASSWORD=change-me-locally-only
```

`DEV_LOGIN_ENABLED` defaults to `true`, which is what we want locally.

## 2. Start the stack

```bash
# apply database migrations once
docker compose --profile migration run --rm migrate

# bring everything up
docker compose up -d
```

This starts PostgreSQL (`:5432`), the API (`:8000`), the MCP tool server
(`:8001`), and the React console (`:8501`).

The API compiles three LangGraph graphs on startup, so `/health` takes ~1–2
minutes to go green. Wait for it:

```bash
until curl -sf http://localhost:8000/health >/dev/null; do sleep 3; done
echo "API is healthy"
```

Expected `GET /health` body:

```json
{ "status": "healthy", "database": "connected", "graph": "compiled" }
```

## 3. Get a token

Every non-public route needs a bearer JWT. Log in as the seeded sales rep
(`rep-1`, role `sales_rep`):

```bash
REP=$(curl -s http://localhost:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"user_id":"rep-1","password":"change-me-locally-only"}' | jq -r .access_token)
```

## 4. Run the workflow

```bash
RUN=$(curl -s -X POST http://localhost:8000/workflows/run \
  -H "Authorization: Bearer $REP" \
  -H 'Content-Type: application/json' \
  -d '{"workflow_type":"sales_ops","lead_data":{"company_name":"Stripe"}}')
echo "$RUN" | jq .
```

Expected response:

```json
{
  "run_id": "…",
  "thread_id": "…",
  "status": "awaiting_approval",
  "message": "Proposal drafted; awaiting human approval"
}
```

The supervisor routed the run through `researcher` → `analyzer` → `executor`,
which drafted a proposal — then the graph **interrupted** for human approval and
persisted a checkpoint. Nothing was sent yet.

> **Note:** `sales_ops` is the only production-ready workflow. `support_ops` and
> `finance_recon` are scaffolds and must be called with `"dry_run": true`.

## 5. Approve the proposal

Approvals require the `manager` role (separation of duties). Get a manager token
and resolve the pending request:

```bash
MGR=$(curl -s http://localhost:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"user_id":"manager-1","password":"change-me-locally-only"}' | jq -r .access_token)

TOKEN=$(curl -s http://localhost:8000/approvals/pending \
  -H "Authorization: Bearer $MGR" | jq -r '.[0].token')

curl -s -X POST "http://localhost:8000/approvals/$TOKEN/approve" \
  -H "Authorization: Bearer $MGR" \
  -H 'Content-Type: application/json' \
  -d '{"note":"Good fit — send it"}' | jq .
```

The graph resumes from its checkpoint and completes.

## 6. See it in the console

Open **http://localhost:8501** and go to **Console → Live runs** and
**Approvals**. You'll see the run and the decision you just made.

You can also read the final state from the API:

```bash
curl -s "http://localhost:8000/workflows/$(echo "$RUN" | jq -r .run_id)" \
  -H "Authorization: Bearer $REP" | jq '{status, total_cost_usd, total_tokens}'
```

## Expected result

- A completed `sales_ops` run visible in the console.
- One approval decision in the Approvals activity.
- A non-zero `total_cost_usd` (the LLM calls you just paid for).

## Troubleshooting

| Symptom | Fix |
|---|---|
| `401 Unauthorized` | You didn't send `Authorization: Bearer $REP`. |
| `403 Forbidden` on approve | You used the rep token; approvals need `manager-1`. |
| `relation ... does not exist` | Run the migration step (2) first. |
| `/health` never green | Give it 1–2 min; poll, don't assume failure. |
| `504` on run | Raised `WORKFLOW_RUN_TIMEOUT_SECONDS`? A tool/LLM hung. |

Full list: [troubleshooting.md](../troubleshooting.md).

## Next steps

- [Stream & debug a run](03-streaming-and-debugging.md) — watch it think in real time.
- [Run offline with Ollama](02-run-offline-with-ollama.md) — no OpenAI key.
- [Semantic memory](04-semantic-memory.md) — give agents recall.
- [API reference](../api-reference.md) · [Glossary](../glossary.md)
