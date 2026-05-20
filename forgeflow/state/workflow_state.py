"""WorkflowState — the single TypedDict that flows through every graph node.

Reducer semantics:
  - add_messages  → append messages, dedup by ID (standard LangGraph pattern)
  - operator.add  → list concatenation (accumulate results across agent hops)
  - no reducer    → last-write-wins (simple override, used for routing decisions)
"""

from __future__ import annotations

from operator import add
from typing import Annotated

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class WorkflowState(TypedDict):
    # ------------------------------------------------------------------ #
    # Message channel — add_messages handles dedup by message ID          #
    # ------------------------------------------------------------------ #
    messages: Annotated[list[BaseMessage], add_messages]

    # ------------------------------------------------------------------ #
    # Accumulator fields — results append across agent hops               #
    # ------------------------------------------------------------------ #
    research_results: Annotated[list[dict], add]
    analysis_scores: Annotated[list[dict], add]
    executed_actions: Annotated[list[str], add]
    errors: Annotated[list[str], add]

    # ------------------------------------------------------------------ #
    # Override fields — last write wins, no reducer                       #
    # ------------------------------------------------------------------ #
    workflow_id: str
    thread_id: str

    # Routing: supervisor writes this, conditional edge reads it
    current_stage: str       # qualify | research | analyze | propose | approve | done
    next_agent: str | None   # researcher | analyzer | executor | human_approval | FINISH

    # Sales domain data
    lead_id: str | None
    lead_data: dict | None
    proposal: dict | None

    # Human-in-the-loop
    approval_status: str | None   # pending | approved | rejected
    approval_token: str | None    # UUID stored in approval_requests table

    # Cost tracking (updated by CostTracker after each LLM call)
    total_tokens: int
    total_cost_usd: float

    # Dry-run flag — when True, side-effecting tools (CRM writes, emails,
    # Slack posts) are skipped and a stub response is returned. LLM calls
    # still happen so the workflow plan is exercised end-to-end.
    dry_run: bool

    # Metadata forwarded to LangSmith and audit log
    run_metadata: dict           # {user_id, role, budget_limit, langsmith_tags}
