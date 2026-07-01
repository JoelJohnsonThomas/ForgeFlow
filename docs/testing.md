# Testing

ForgeFlow ships **344 tests** across `tests/unit/` and `tests/integration/`. The
suite is designed to be **hermetic** — it mocks I/O so it runs offline and in CI
without real credentials or network.

## Running tests

```bash
pip install -e '.[dev]'          # pytest, pytest-asyncio, pytest-cov, ruff, mypy
make test                        # full suite with coverage
make test-unit                   # fast unit tests only
make test-integration            # integration tests
pytest tests/unit/test_jwt.py -q # a single file
pytest -k "idor or refresh"      # by keyword
```

`pytest` is configured in `pyproject.toml` (`asyncio_mode = "auto"`, so `async`
tests need no decorator; `testpaths = ["tests"]`).

## How the suite stays hermetic

`tests/conftest.py` sets safe defaults and provides shared fixtures:

- **Env defaults** — fake `OPENAI_API_KEY`, test Postgres DSNs, tracing off, so
  imports never require real config.
- **`_stub_dns` (autouse)** — stubs `socket.getaddrinfo` to a fixed public IP so
  the SSRF guard's real logic runs while **no test touches the network**.
- **`mock_llm`** — a deterministic `ChatOpenAI` stand-in.
- **`mock_pool`** — a mocked asyncpg pool (`fetchrow`/`fetch`/`execute`).

Because the pool is mocked, most tests never hit a database — fast, but see the
caveat below.

## Test types

| Type | Location | Style |
|---|---|---|
| **Unit** | `tests/unit/` | Pure functions + mocked collaborators (RBAC, JWT, connectors, guards, config) |
| **Integration** | `tests/integration/` | Cross-module, e.g. FastAPI `TestClient` with mocked pool/graph, MCP tool invocation |
| **DB-integration** | `tests/integration/test_auth_db.py` | Runs against a **live Postgres**, skips cleanly when unreachable |
| **E2E (frontend)** | `frontend/e2e/` | Playwright against the console (`npm run test:e2e`) |

### DB-integration pattern

`test_auth_db.py` connects to the compose Postgres (`127.0.0.1:5433` by default,
override with `FF_TEST_DSN`) and **skips** if it can't — so CI without a DB stays
green while a local run exercises real SQL (refresh-token rotation + reuse
detection). This is the pattern to copy when you need real-schema coverage.

> **Known gap / caveat:** because unit tests mock the pool, a *schema* bug can
> pass all mocked tests and still fail in production (this is exactly how an
> earlier `resolved_by` type mismatch shipped). When you touch SQL or a
> migration, add a DB-integration test like `test_auth_db.py`.

## Writing tests

- Put unit tests next to their peers in `tests/unit/`, name files `test_*.py`.
- Use the `mock_llm` / `mock_pool` fixtures rather than rolling your own.
- For API routes, use `fastapi.testclient.TestClient` and patch
  `init_pool`/`compile_graph`/`get_mcp_tools` (see `tests/integration/test_api.py`).
- Cover the **negative** paths: 401/403/422, invalid input, reuse/expiry.
- For anything that runs SQL, add a skip-guarded DB-integration test.

Example (object-level authorization, pure unit):
```python
import pytest
from fastapi import HTTPException
from forgeflow.api.routers.workflows import _assert_can_read_run
from forgeflow.rbac.models import UserContext

def test_sales_rep_cannot_read_others_run():
    with pytest.raises(HTTPException) as e:
        _assert_can_read_run(UserContext(user_id="rep-1", role="sales_rep"), row_user_id="rep-2")
    assert e.value.status_code == 404
```

## Coverage

`make test` runs with `pytest-cov` (`--cov=forgeflow`). Aim to keep or raise the
current line coverage; **new SQL/migrations and new endpoints must ship with
tests** (unit for logic, DB-integration for schema, an API test for auth/routing).

## Test analytics (optional)

The suite integrates the TestRelic pytest reporter — set `TESTRELIC_API_KEY` to
upload a run timeline (see `.testrelic/testrelic-config.json`). It silently
no-ops without a key, so it never blocks CI.

## Quality gates

```bash
make lint     # ruff + mypy
make fmt      # ruff format
make test     # pytest + coverage
```
CI (`.github/workflows/ci.yml`) runs these on every PR — keep them green.
