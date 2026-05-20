"""Pure async node functions — thin wrappers that call agents and record traces.

Each function has the signature: async def node_name(state: WorkflowState) -> dict
LangGraph calls these and merges the returned dict into WorkflowState via reducers.

We keep agents as objects (constructed in builder.py) and import them here
via module-level singletons to avoid re-creating LLM clients on every invocation.

Each worker node is wrapped with cost tracking + budget enforcement:
  1. Before invoking the agent, BudgetGuard checks the running total_cost_usd.
     If exceeded, the node short-circuits with an error and next_agent="FINISH".
  2. After the agent returns, any AIMessage usage_metadata is summed and
     converted to cost via calculate_cost(). Totals are accumulated into the
     state patch so the next node sees up-to-date numbers.
"""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING, Any

from forgeflow.observability.cost_tracker import calculate_cost, count_tokens
from forgeflow.resilience.budget_guard import BudgetExceededError, BudgetGuard
from forgeflow.state.workflow_state import WorkflowState

if TYPE_CHECKING:
    from forgeflow.agents.analyzer import AnalyzerAgent
    from forgeflow.agents.base import BaseAgent
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


def _extract_usage(messages: list[Any], model_name: str) -> tuple[int, int]:
    """Sum input + output tokens across any AIMessage with usage_metadata.

    Falls back to a tiktoken estimate from message content when usage_metadata
    is missing (e.g. mocked LLMs in tests).
    """
    input_tokens = 0
    output_tokens = 0
    estimated = False
    for msg in messages:
        usage = getattr(msg, "usage_metadata", None)
        if usage:
            input_tokens += int(usage.get("input_tokens", 0) or 0)
            output_tokens += int(usage.get("output_tokens", 0) or 0)
            continue
        content = getattr(msg, "content", None)
        if isinstance(content, str) and content:
            output_tokens += count_tokens(content, model=model_name)
            estimated = True
    if estimated:
        logger.debug("usage_metadata unavailable for %s; using tiktoken estimate", model_name)
    return input_tokens, output_tokens


async def _run_with_cost_tracking(agent: BaseAgent, state: WorkflowState) -> dict:
    """Wrap agent.safe_run() with a pre-call budget check and post-call cost record."""
    current_cost = float(state.get("total_cost_usd") or 0.0)
    current_tokens = int(state.get("total_tokens") or 0)

    guard = BudgetGuard()
    try:
        guard.check(current_cost)
    except BudgetExceededError as exc:
        logger.warning("Budget exceeded before %s ran: %s", agent.name, exc)
        return {
            "errors": [f"BudgetExceeded: {exc}"],
            "next_agent": "FINISH",
            "total_cost_usd": current_cost,
            "total_tokens": current_tokens,
        }

    patch = await agent.safe_run(state)

    in_tok, out_tok = _extract_usage(patch.get("messages", []) or [], agent.model_name)
    call_cost = calculate_cost(agent.model_name, in_tok, out_tok)

    patch["total_tokens"] = current_tokens + in_tok + out_tok
    patch["total_cost_usd"] = current_cost + call_cost

    logger.debug(
        "Cost tracked | agent=%s model=%s in=%d out=%d call=$%.4f total=$%.4f",
        agent.name,
        agent.model_name,
        in_tok,
        out_tok,
        call_cost,
        patch["total_cost_usd"],
    )
    return patch


async def supervisor_node(state: WorkflowState) -> dict:
    assert _supervisor is not None, "Supervisor agent not initialised"
    return await _run_with_cost_tracking(_supervisor, state)


async def researcher_node(state: WorkflowState) -> dict:
    assert _researcher is not None, "Researcher agent not initialised"
    return await _run_with_cost_tracking(_researcher, state)


async def analyzer_node(state: WorkflowState) -> dict:
    assert _analyzer is not None, "Analyzer agent not initialised"
    return await _run_with_cost_tracking(_analyzer, state)


async def executor_node(state: WorkflowState) -> dict:
    assert _executor is not None, "Executor agent not initialised"
    return await _run_with_cost_tracking(_executor, state)


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
