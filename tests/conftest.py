"""Shared pytest fixtures for unit and integration tests."""

from __future__ import annotations

import os
import socket
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage

# Ensure test env vars are set before any imports
os.environ.setdefault("OPENAI_API_KEY", "sk-test-fake-key-for-testing")
os.environ.setdefault("POSTGRES_URL", "postgresql+asyncpg://forgeflow:testpass@localhost:5432/forgeflow_test")
os.environ.setdefault("POSTGRES_SYNC_URL", "postgresql+psycopg://forgeflow:testpass@localhost:5432/forgeflow_test")
os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")
os.environ.setdefault("API_SECRET_KEY", "test-secret")
os.environ.setdefault("BUDGET_LIMIT_USD", "10.0")
# support_ops + finance_recon are template scaffolds — their .run() raises in
# production unless dry_run=True. Tests bypass the guard via this opt-in flag
# (also documented in the pipelines' module docstrings).
os.environ.setdefault("FORGEFLOW_ALLOW_TEMPLATE_WORKFLOWS", "1")

# The TestRelic reporter (testrelic-pytest) reads TESTRELIC_API_KEY from the OS
# environment, but pytest doesn't auto-load .env where the rest of our config
# lives. Surface the TestRelic keys here so a bare `pytest` reports runs without
# a manual `export`. We never override an already-set value (CI secrets win),
# and the plugin silently no-ops when the key is absent.
from dotenv import dotenv_values, find_dotenv  # noqa: E402

_dotenv = dotenv_values(find_dotenv())
for _key in ("TESTRELIC_API_KEY", "TESTRELIC_PROJECT_NAME", "TESTRELIC_UPLOAD_STRATEGY"):
    _val = _dotenv.get(_key)
    if _val and not os.environ.get(_key):
        os.environ[_key] = _val


@pytest.fixture(autouse=True)
def _stub_dns(monkeypatch):
    """Make the test suite hermetic by stubbing DNS resolution.

    The SSRF guard (forgeflow.security.ssrf_guard.check_url) calls
    socket.getaddrinfo on every outbound connector request. Unit tests mock the
    HTTP transport but not DNS, so on a network-less runner the guard raised
    SSRFBlocked before the mocked client was ever reached. We resolve every host
    to a fixed public IP (example.com's address) so the guard's real logic —
    scheme, userinfo, IP-literal and private-range checks — still runs, while
    no test touches the network. Tests that need to exercise private-range
    rejection can pass IP literals (which skip getaddrinfo entirely).
    """
    public_ip = "93.184.216.34"  # example.com — globally routable

    def _fake_getaddrinfo(host, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (public_ip, 0))]

    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo)


@pytest.fixture
def mock_llm():
    """Returns a deterministic ChatOpenAI mock."""
    llm = MagicMock()
    llm.ainvoke = AsyncMock(
        return_value=AIMessage(
            content='{"next": "researcher", "reasoning": "test routing"}',
            name="mock",
        )
    )
    llm.with_structured_output = MagicMock(return_value=llm)
    llm.bind_tools = MagicMock(return_value=llm)
    return llm


@pytest.fixture
def mock_pool():
    """Mock asyncpg pool for unit tests."""
    pool = MagicMock()
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=None)
    conn.fetch = AsyncMock(return_value=[])
    conn.execute = AsyncMock(return_value="OK")
    pool.acquire = MagicMock(return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=conn),
        __aexit__=AsyncMock(return_value=None),
    ))
    return pool


@pytest.fixture
def sample_workflow_state():
    """Returns a minimal valid WorkflowState for testing."""
    return {
        "messages": [],
        "research_results": [],
        "analysis_scores": [],
        "executed_actions": [],
        "errors": [],
        "workflow_id": "test-workflow-123",
        "thread_id": "test-thread-456",
        "current_stage": "qualify",
        "next_agent": None,
        "lead_id": None,
        "lead_data": {"company_name": "Acme Corp", "industry": "saas"},
        "proposal": None,
        "approval_status": None,
        "approval_token": None,
        "total_tokens": 0,
        "total_cost_usd": 0.0,
        "dry_run": False,
        "run_metadata": {"user_id": "test-user", "role": "sales_rep"},
    }
