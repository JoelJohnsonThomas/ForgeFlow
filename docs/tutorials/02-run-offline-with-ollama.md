# Tutorial 2 — Run fully offline with Ollama

**Goal:** run ForgeFlow workflows against a **local** LLM — no OpenAI/Anthropic
key, no outbound calls to a model provider. This is the same path used for
air-gapped deployments.

**Time:** ~15 minutes (plus model download).

## Prerequisites

- Tutorial 1's stack config (repo cloned, `.env` created). You do **not** need an
  `OPENAI_API_KEY` for this one.
- [Ollama](https://ollama.com/) installed and running on the host.

## 1. Pull the models

ForgeFlow uses two model tiers — a cheap default and a stronger one for the
supervisor and the judge. The defaults are small enough to run on a laptop:

```bash
ollama pull llama3.2:3b     # default (OLLAMA_MODEL)
ollama pull llama3.1:8b     # strong  (OLLAMA_MODEL_STRONG)
```

Confirm the daemon is reachable:

```bash
curl -s http://localhost:11434/api/tags | jq '.models[].name'
```

## 2. Point ForgeFlow at Ollama

In `.env`:

```bash
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434   # from inside the container
OLLAMA_MODEL=llama3.2:3b
OLLAMA_MODEL_STRONG=llama3.1:8b
```

> **Note:** from inside Docker, use `host.docker.internal` (not `localhost`) to
> reach the Ollama daemon on your host. On Linux you may need
> `--add-host=host.docker.internal:host-gateway` or the host's LAN IP. The
> config default `http://localhost:11434` is correct when the API runs on the
> host instead of in a container.

## 3. Restart and run

```bash
docker compose up -d          # picks up the new .env
until curl -sf http://localhost:8000/health >/dev/null; do sleep 3; done
```

Then run `sales_ops` exactly as in [Tutorial 1](01-first-workflow.md#3-get-a-token) —
the API call is identical; only the model backend changed:

```bash
REP=$(curl -s http://localhost:8000/auth/login -H 'Content-Type: application/json' \
  -d '{"user_id":"rep-1","password":"change-me-locally-only"}' | jq -r .access_token)

curl -s -X POST http://localhost:8000/workflows/run \
  -H "Authorization: Bearer $REP" -H 'Content-Type: application/json' \
  -d '{"workflow_type":"sales_ops","lead_data":{"company_name":"Stripe"}}' | jq '{status}'
```

## Expected result

- The run completes (or pauses for approval) **with no external LLM billing** —
  `total_cost_usd` is `0` for local models.
- Enterprise connectors without credentials run as **mocks**, so no external
  network calls are required for the demo.

## Notes & limits

- **Quality/latency:** small local models are weaker and slower than `gpt-4o`.
  For better results with more RAM/VRAM, pull larger models and set
  `OLLAMA_MODEL_STRONG` accordingly.
- **Web search:** without `TAVILY_API_KEY`, the researcher uses mock search
  results — expected in an offline setup.
- **True air-gap:** for a signed offline bundle and zero-egress deployment, see
  [deployment/AIRGAPPED.md](../deployment/AIRGAPPED.md).

## Troubleshooting

| Symptom | Fix |
|---|---|
| API can't reach Ollama | Use `host.docker.internal`, not `localhost`, from the container. |
| `model not found` | `ollama pull` the exact tags in `OLLAMA_MODEL*`. |
| Very slow runs | Expected for local models; try a smaller model or more hardware. |

## Next steps

- [Stream & debug a run](03-streaming-and-debugging.md)
- [Air-gapped deployment](../deployment/AIRGAPPED.md)
- [Configuration reference](../configuration.md#llm-provider)
