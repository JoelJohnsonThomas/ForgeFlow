# Examples

Practical, runnable patterns. All assume the stack is up
([Quickstart](../README.md#-quickstart)) and you have a token
([auth](auth.md)).

## 1. End-to-end via the API (curl)

```bash
# Get tokens (rep executes, manager approves)
REP=$(curl -s localhost:8000/auth/login -H 'Content-Type: application/json' \
  -d '{"user_id":"rep-1","password":"change-me-locally-only"}' | jq -r .access_token)
MGR=$(curl -s localhost:8000/auth/login -H 'Content-Type: application/json' \
  -d '{"user_id":"manager-1","password":"change-me-locally-only"}' | jq -r .access_token)

# Trigger a run
RUN=$(curl -s -X POST localhost:8000/workflows/run -H "Authorization: Bearer $REP" \
  -H 'Content-Type: application/json' \
  -d '{"lead_data":{"company_name":"Stripe"},"workflow_type":"sales_ops"}')
echo "$RUN" | jq .

# If it paused for approval, approve it
TOKEN=$(curl -s localhost:8000/approvals/pending -H "Authorization: Bearer $MGR" | jq -r '.[0].token')
curl -s -X POST "localhost:8000/approvals/$TOKEN/approve" -H "Authorization: Bearer $MGR" \
  -H 'Content-Type: application/json' -d '{"note":"Good fit"}' | jq .
```

## 2. Run a workflow programmatically (Python)

Against the running API with `httpx`:

```python
import httpx

BASE = "http://localhost:8000"
with httpx.Client(timeout=120) as c:
    tok = c.post(f"{BASE}/auth/login",
                 json={"user_id": "rep-1", "password": "change-me-locally-only"}
                 ).json()["access_token"]
    h = {"Authorization": f"Bearer {tok}"}
    run = c.post(f"{BASE}/workflows/run", headers=h,
                 json={"lead_data": {"company_name": "Acme"}, "workflow_type": "sales_ops"}).json()
    status = c.get(f"{BASE}/workflows/{run['run_id']}", headers=h).json()
    print(status["status"], status["total_cost_usd"])
```

Or in-process (no HTTP), using the pipeline directly:

```python
from forgeflow.workflows.sales_ops.pipeline import SalesOpsPipeline
from forgeflow.workflows.sales_ops.models import LeadInput
from forgeflow.graph.builder import compile_graph

graph = await compile_graph(mcp_tools=[], workflow_type="sales_ops")
run_id, thread_id, state = await SalesOpsPipeline(graph).run(
    LeadInput(company_name="Acme"), user_id="rep-1", role="sales_rep", dry_run=True
)
```

## 3. Stream agent reasoning (SSE)

```python
import httpx

with httpx.stream("POST", "http://localhost:8000/workflows/stream",
                  headers={"Authorization": f"Bearer {tok}"},
                  json={"lead_data": {"company_name": "Stripe"}, "workflow_type": "sales_ops"}
                  ) as r:
    for line in r.iter_lines():
        if line.startswith("data: "):
            print(line[6:])   # {"event":"node_complete","node":"researcher",...}
```

## 4. Add a custom connector

```python
# forgeflow/connectors/acme.py
from forgeflow.config import get_settings
from forgeflow.connectors.base import BaseConnector

class AcmeConnector(BaseConnector):
    vendor = "acme"

    def __init__(self, token: str | None = None) -> None:
        s = get_settings()
        super().__init__(base_url=s.acme_base_url,
                         token=token if token is not None else s.acme_api_key.get_secret_value())

    async def get_widget(self, widget_id: str) -> dict:
        return await self._request("GET", f"/widgets/{widget_id}")
```
Then add `acme_api_key` / `acme_base_url` to `forgeflow/config.py`, expose an MCP
tool router under `forgeflow/mcp/server/tools/acme_tools.py`, and mount it in
`forgeflow/mcp/server/main.py`. The base class gives you retry-with-backoff,
`Retry-After` handling, SSRF checks, and graceful mock degradation for free.
See [connectors.md](connectors.md).

## 5. Add a workflow template

```yaml
# templates/community/my_workflow/manifest.yaml
name: my_workflow
version: "1.0.0"
description: What this template does.
domain: sales_ops          # must map to a workflow pipeline
stages: [qualify, research, analyze, approve]
input_schema:
  company_name: { type: string, required: true }
```
Validate it (pass the **file**, not the directory):
```bash
python scripts/marketplace.py validate templates/community/my_workflow/manifest.yaml
```
Working example: [`templates/community/lead_triage/`](../templates/community/lead_triage/manifest.yaml).

## 6. Error handling in connectors

Connectors distinguish retryable from permanent failures so workflows can branch:

```python
from forgeflow.connectors.base import RetryableError, PermanentError

try:
    result = await connector.get_widget("123")
except RetryableError:
    ...  # transient (429/503/timeout) — the workflow can re-drive
except PermanentError:
    ...  # auth/validation/404 — needs human attention, don't retry
```

## 7. Dry-run (no side effects)

Add `"dry_run": true` to any `/workflows/run` call. The LLM plan still executes,
but CRM writes, emails, and Slack posts are skipped and stubbed. Useful for the
template scaffolds (`support_ops`, `finance_recon`) which otherwise refuse to run.
