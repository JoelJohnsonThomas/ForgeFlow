"""Pure async node functions — thin wrappers that call agents and record traces.

Each function has the signature: async def node_name(state: WorkflowState) -> dict
LangGraph calls these and merges the returned dict into WorkflowState via reducers.

We keep agents as objects (constructed in builder.py) and import them here
via module-level singletons to avoid re-creating LLM clients on every invocation.
"""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

from forgeflow.state.workflow_state import WorkflowState

if TYPE_CHECKING:
    from forgeflow.agents.analyzer import AnalyzerAgent
    from forgeflow.agents.executor import ExecutorAgent
    from forgeflow.agents.researcher import ResearcherAgent
    from forgeflow.agents.supervisor import SupervisorAgent

logger = logging.getLogger(__name__)

# Agent singletons — set by build_node_factory() in builder.py
_supervisor: SupervisorAgent | None = None
_researcher: ResearcherAgent | None = None
_analyzer: AnalyzerAgent | None = None
_executor: ExecutorAgent | None = None


def build_node_factory(
    supervisor: SupervisorAgent,
    researcher: ResearcherAgent,
    analyzer: AnalyzerAgent,
    executor: ExecutorAgent,
) -> None:
    global _supervisor, _researcher, _analyzer, _executor
    _supervisor = supervisor
    _researcher = researcher
    _analyzer = analyzer
    _executor = executor


async def supervisor_node(state: WorkflowState) -> dict:
    assert _supervisor is not None, "Supervisor agent not initialised"
    return await _supervisor.safe_run(state)


async def researcher_node(state: WorkflowState) -> dict:
    assert _researcher is not None, "Researcher agent not initialised"
    return await _researcher.safe_run(state)


async def analyzer_node(state: WorkflowState) -> dict:
    assert _analyzer is not None, "Analyzer agent not initialised"
    return await _analyzer.safe_run(state)


async def executor_node(state: WorkflowState) -> dict:
    assert _executor is not None, "Executor agent not initialised"
    return await _executor.safe_run(state)


async def human_approval_node(state: WorkflowState) -> dict:
    """Suspended node — LangGraph interrupts here before execution.

    When the graph is resumed (POST /approvals/{token}/approve), this node
    runs with the updated state that includes approval_status.
    The actual routing happens in edges.route_human_approval().
    """
    approval_status = state.get("approval_status", "pending")
    approval_token = state.get("approval_token") or str(uuid.uuid4())

    logger.info(
        "Human approval node | status=%s | token=%s",
        approval_status,
        approval_token,
    )

    return {
        "approval_token": approval_token,
        "approval_status": approval_status,
    }
