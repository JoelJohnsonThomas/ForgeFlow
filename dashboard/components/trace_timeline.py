"""Plotly Gantt chart for agent execution trace visualization."""

from __future__ import annotations

from datetime import datetime

import plotly.figure_factory as ff
import streamlit as st

AGENT_COLORS = {
    "supervisor": "#4F8EF7",
    "researcher": "#2ECC71",
    "analyzer": "#F39C12",
    "executor": "#E74C3C",
    "human_approval": "#9B59B6",
}


def render_trace_gantt(traces: list[dict]) -> None:
    """Render an agent execution timeline using a Plotly Gantt chart."""
    if not traces:
        st.info("No trace data available for this run.")
        return

    tasks = []
    for trace in traces:
        started = trace.get("started_at")
        completed = trace.get("completed_at")
        if not started:
            continue
        if not completed:
            completed = started

        # Parse timestamps if they're strings
        if isinstance(started, str):
            started = datetime.fromisoformat(started.replace("Z", "+00:00"))
        if isinstance(completed, str):
            completed = datetime.fromisoformat(completed.replace("Z", "+00:00"))

        agent = trace.get("agent_name", "unknown")
        tasks.append({
            "Task": agent,
            "Start": started,
            "Finish": completed,
            "Resource": trace.get("stage", ""),
            "Description": (
                f"Tokens: {trace.get('tokens_used', 0)} | "
                f"Cost: ${float(trace.get('cost_usd', 0)):.4f}"
            ),
        })

    if not tasks:
        st.warning("No completed trace records found.")
        return

    colors = [AGENT_COLORS.get(t["Task"], "#95A5A6") for t in tasks]

    fig = ff.create_gantt(
        tasks,
        colors=colors,
        index_col="Task",
        show_colorbar=True,
        group_tasks=True,
        title="Agent Execution Timeline",
    )
    fig.update_layout(
        height=300,
        margin=dict(l=10, r=10, t=50, b=10),
        font=dict(size=12),
    )
    st.plotly_chart(fig, use_container_width=True)
