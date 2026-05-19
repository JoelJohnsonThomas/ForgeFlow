"""LangSmith tracing helpers — inject metadata into graph invocations.

LangSmith traces automatically when LANGCHAIN_TRACING_V2=true.
These helpers add structured metadata (workflow_id, user, cost) to each run
so traces are queryable and filterable in the LangSmith dashboard.
"""

from __future__ import annotations

from forgeflow.state.workflow_state import WorkflowState


def get_run_config(state: WorkflowState, run_name: str | None = None) -> dict:
    """Build the LangSmith-compatible config dict for graph.ainvoke().

    Pass this as the `config` argument to preserve trace metadata across
    all node invocations within the run.
    """
    meta = state.get("run_metadata", {})
    stage = state.get("current_stage", "unknown")
    workflow_id = state.get("workflow_id", "")
    thread_id = state.get("thread_id", "")
    company = (state.get("lead_data") or {}).get("company_name", "")

    tags = meta.get("langsmith_tags", []) + [
        f"stage:{stage}",
        f"workflow:{workflow_id[:8]}",
    ]
    if company:
        tags.append(f"company:{company.lower()[:20]}")

    return {
        "run_name": run_name or f"forgeflow/{stage}/{company}",
        "tags": tags,
        "metadata": {
            "workflow_id": workflow_id,
            "thread_id": thread_id,
            "current_stage": stage,
            "user_id": meta.get("user_id", "anon"),
            "role": meta.get("role", "unknown"),
            "lead_company": company,
        },
        "configurable": {
            "thread_id": thread_id,
        },
    }
