"""Shared pytest fixtures for unit and integration tests."""

from __future__ import annotations

import os
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
