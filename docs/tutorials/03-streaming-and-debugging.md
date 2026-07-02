# Tutorial 3 — Stream & debug a run

**Goal:** watch a workflow reason in real time over server-sent events (SSE),
read the per-agent trace after it finishes, and diagnose the common failure
modes.

**Time:** ~10 minutes.

## Prerequisites

- A running stack and a token (`$REP`) from [Tutorial 1](01-first-workflow.md).

## 1. Stream the run (SSE)

`POST /workflows/stream` runs the same graph as `/run` but emits an event per
node as it happens. With `curl -N` (no buffering):

```bash
curl -N -X POST http://localhost:8000/workflows/stream \
  -H "Authorization: Bearer $REP" \
  -H 'Content-Type: application/json' \
  -d '{"workflow_type":"sales_ops","lead_data":{"company_name":"Stripe"}}'
```

You'll see a stream of `data:` lines, one per node transition, e.g.:

```
data: {"event":"node_complete","node":"researcher","tokens":2431,"cost_usd":0.024}
data: {"event":"node_complete","node":"analyzer","score":8.4}
data: {"event":"interrupt","node":"human_approval","token":"apr_…"}
```

In Python:

```python
import httpx

with httpx.stream("POST", "http://localhost:8000/workflows/stream",
                  headers={"Authorization": f"Bearer {tok}"},
                  json={"workflow_type": "sales_ops",
                        "lead_data": {"company_name": "Stripe"}}) as r:
    for line in r.iter_lines():
        if line.startswith("data: "):
            print(line[6:])
```

## 2. Read the per-agent trace

After a run, fetch each agent's prompt and output (subject to ownership — you can
read your own runs). Set `RUN_ID` to a `run_id` returned by a previous
`/workflows/run` call:

```bash
RUN_ID=…   # a run_id from step 1 or Tutorial 1
curl -s "http://localhost:8000/workflows/$RUN_ID/trace" \
  -H "Authorization: Bearer $REP" | jq '.[] | {agent, tokens, cost_usd}'
```

Use this to see *why* the supervisor routed the way it did and what each worker
produced.

## 3. Check cost and evaluation

```bash
# spend for the last 7 days, by agent
curl -s "http://localhost:8000/metrics/cost?days=7" -H "Authorization: Bearer $REP" | jq .

# LLM-as-judge quality summary
curl -s "http://localhost:8000/metrics/evaluation" -H "Authorization: Bearer $REP" | jq .
```

The console surfaces the same data under **Cost & spend** and **Evaluations**.

## Debugging checklist

| Symptom | Likely cause | Action |
|---|---|---|
| Run returns `504` | A tool or LLM call hung past `WORKFLOW_RUN_TIMEOUT_SECONDS` (default 180s) | Inspect the trace for the slow node; raise the timeout or fix the dependency. |
| Run halts early, "budget" | Per-run `BUDGET_LIMIT_USD` (default $5) reached | Raise it for legitimate large runs. |
| `5xx` after retries | Upstream/LLM failure past the circuit breaker | Check the provider; the breaker opens after `CIRCUIT_BREAKER_THRESHOLD` failures. |
| Empty/mock research | No `TAVILY_API_KEY` | Set it for real web search; mocks are expected otherwise. |
| Stream shows no events | Missing `-N` (curl buffering) or missing token | Add `-N`; send the bearer header. |

Full reference: [troubleshooting.md](../troubleshooting.md).

## Next steps

- [Semantic memory](04-semantic-memory.md)
- [API reference → Workflows](../api-reference.md#workflows)
- [Architecture → request lifecycle](../architecture.md#api-request-lifecycle)
