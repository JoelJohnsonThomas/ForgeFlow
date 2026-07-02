# Tutorial 5 — Author a custom tool

**Goal:** add your own tool to ForgeFlow's MCP server and have agents pick it up
automatically. You'll write a tool, mount it, restart the server, and confirm
agents can call it.

**Time:** ~20 minutes.

## Prerequisites

- A working checkout and the stack from [Tutorial 1](01-first-workflow.md).
- Comfort editing Python. Tools live in the `forgeflow` package.

## Concepts

ForgeFlow exposes tools to agents over the
[Model Context Protocol (MCP)](https://modelcontextprotocol.io/):

- The **MCP server** (`forgeflow/mcp/server/main.py`, port `8001`) is a
  [FastMCP](https://github.com/jlowin/fastmcp) app.
- Each provider is a small **router** — a `FastMCP` instance whose functions are
  decorated with `@router.tool()`.
- `main.py` composes them with `mcp.mount(module.router, prefix="…")`.
- Agents load **all** mounted tools automatically through the client adapter
  (`forgeflow/mcp/client/adapter.py` → `get_mcp_tools()`). There is no per-tool
  client wiring: mount it on the server and it's available to agents.

## 1. Write the tool

Create `forgeflow/mcp/server/tools/acme_tools.py`. A tool is an `async` function
with **typed parameters** and a **docstring** — the docstring is the description
the LLM sees, so make it count.

```python
"""MCP tools: Acme widget lookup."""
from __future__ import annotations

import logging

from fastmcp import FastMCP

from forgeflow.config import get_settings

logger = logging.getLogger(__name__)

router = FastMCP("acme-tools")


@router.tool()
async def get_widget(widget_id: str) -> dict:
    """Look up an Acme widget by id.

    Args:
        widget_id: The widget identifier, e.g. "wgt_123".

    Returns:
        A dict with the widget's fields, or an {"error": ...} dict.
    """
    settings = get_settings()

    # Graceful degradation: return a mock when the integration isn't configured,
    # so demos and CI run without credentials (this is the house pattern).
    if not getattr(settings, "acme_api_key", None):
        logger.warning("Acme not configured — returning a mock widget")
        return {"id": widget_id, "name": "Mock widget", "in_stock": True, "mock": True}

    # Real call goes here — prefer a connector (step 3) for retries + SSRF.
    return {"id": widget_id, "name": "Blue widget", "in_stock": True}
```

> **Note:** return only JSON-serializable values (`dict`, `list`, `str`,
> numbers). Tools that fetch **arbitrary URLs** must go through the SSRF guard —
> see `scrape_url` in
> [`search_tools.py`](https://github.com/JoelJohnsonThomas/forgeflow/blob/main/forgeflow/mcp/server/tools/search_tools.py)
> and `forgeflow/security/ssrf_guard.py`.

## 2. Mount it on the server

Edit `forgeflow/mcp/server/main.py`: import the module and mount its router with
a prefix (the prefix namespaces your tools alongside the built-ins).

```python
from forgeflow.mcp.server.tools import (
    # …existing imports…
    acme_tools,
)

# …after the other mounts…
mcp.mount(acme_tools.router, prefix="acme")
```

## 3. (Optional) Back it with a connector

For anything that calls an external API, subclass `BaseConnector`
(`forgeflow/connectors/base.py`) instead of using `httpx` directly — you get
retry-with-backoff, `Retry-After` handling, SSRF checks, and mock degradation for
free. This mirrors the eight shipped connectors.

```python
# forgeflow/connectors/acme.py
from forgeflow.config import get_settings
from forgeflow.connectors.base import BaseConnector

class AcmeConnector(BaseConnector):
    vendor = "acme"

    def __init__(self, token: str | None = None) -> None:
        s = get_settings()
        super().__init__(
            base_url=s.acme_base_url,
            token=token if token is not None else s.acme_api_key.get_secret_value(),
        )

    async def get_widget(self, widget_id: str) -> dict:
        return await self._request("GET", f"/widgets/{widget_id}")
```

Add `acme_api_key` / `acme_base_url` to `forgeflow/config.py`, then have the tool
call the connector. Distinguish retryable from permanent failures with
`RetryableError` / `PermanentError` (see
[examples.md](../examples.md#6-error-handling-in-connectors)).

## 4. Restart the MCP server

The tool is registered at server startup, so restart it after mounting.

```bash
# Docker (the service is named mcp_server):
docker compose build mcp_server && docker compose up -d mcp_server

# …or, running the server on the host:
python -m forgeflow.mcp.server.main http
```

## 5. Verify agents can see it

Agents load tools when a workflow starts. Trigger a run
([Tutorial 1, step 4](01-first-workflow.md#4-run-the-workflow)) and check the
**API** logs — the adapter logs the tool count on connect:

```
Loaded N tools from MCP server at http://mcp_server:8001/mcp
```

`N` should have increased by the number of tools you added. The MCP server also
exposes a liveness probe at `GET http://localhost:8001/health`.

> **Note:** there is no REST tool-catalog endpoint yet, so the console's
> **Tools · MCP** view is a static reference — it won't list your new tool
> automatically. Confirm via the log line above.

## Expected result

- A new tool module mounted under the `acme` prefix.
- The API's "Loaded N tools" count reflects your additions.
- Agents in a run can call the tool (the LLM decides when, based on your
  docstring).

## Best practices

- **Type every parameter** and write a precise docstring — that's the tool's
  contract with the model.
- **Degrade to a mock** when credentials are missing, so CI/demos stay green.
- **Never** return secrets or raw credentials from a tool.
- **SSRF-guard** any tool that fetches a user-supplied URL.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Tool count didn't change | Did you `mcp.mount(...)` it and restart `mcp_server`? |
| `ModuleNotFoundError` in the container | Rebuild the image: `docker compose build mcp_server`. |
| Agent never calls the tool | The docstring may be unclear; make the purpose and args explicit. |
| External call fails intermittently | Wrap it in a `BaseConnector` for retries (step 3). |

## Next steps

- [Examples → custom connector](../examples.md#4-add-a-custom-connector)
- [Connectors reference](../connectors.md)
- [Architecture → MCP tool topology](../architecture.md)
- [Glossary → MCP / MCP tool / connector](../glossary.md#tools--agents)
