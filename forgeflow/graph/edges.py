"""Conditional edge routing functions for the LangGraph StateGraph.

Each function reads from WorkflowState and returns a string key that maps
to the next node name in the graph's edge table.
"""

from __future__ import annotations

from forgeflow.state.workflow_state import WorkflowState


def route_supervisor(state: WorkflowState) -> str:
    """Primary routing decision from the supervisor node.

    Reads state['next_agent'] which the SupervisorAgent writes.
    Returns a node name or the END sentinel 'END'.
    """
    next_agent = state.get("next_agent")

    if next_agent in ("researcher", "analyzer", "executor", "human_approval"):
        return next_agent

    # Default to END if supervisor says FINISH or anything unexpected
    return "END"


def route_human_approval(state: WorkflowState) -> str:
    """Routes out of the human_approval node based on the approval decision.

    After a human calls POST /approvals/{token}/approve or /reject, the
    API writes approval_status into the state before resuming the graph.
    """
    approval_status = state.get("approval_status")

    if approval_status == "approved":
        return "executor"

    # rejected, expired, or any other status → end workflow
    return "END"


def route_after_analysis(state: WorkflowState) -> str:
    """Short-circuit: if the lead scored below threshold, skip directly to END.

    This is used as an alternative to always routing back to supervisor — it
    prevents an extra LLM call for the clear disqualify case.
    """
    scores = state.get("analysis_scores", [])
    if not scores:
        return "supervisor"

    latest_score = scores[-1].get("score", 0.0)
    if latest_score < 4.0:
        return "END"

    return "supervisor"
