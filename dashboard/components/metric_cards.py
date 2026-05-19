"""KPI metric card components."""

from __future__ import annotations

import streamlit as st


def render_kpi_row(metrics: dict) -> None:
    """Render the top-level KPI cards row."""
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            label="Total Runs",
            value=int(metrics.get("total_runs", 0)),
        )
    with col2:
        success_rate = metrics.get("success_rate", 0.0)
        st.metric(
            label="Success Rate",
            value=f"{success_rate:.1%}",
        )
    with col3:
        avg_latency = metrics.get("avg_latency_ms", 0.0)
        st.metric(
            label="Avg Latency",
            value=f"{avg_latency/1000:.1f}s",
        )
    with col4:
        avg_cost = metrics.get("avg_cost_usd", 0.0)
        st.metric(
            label="Avg Cost / Run",
            value=f"${avg_cost:.4f}",
        )
    with col5:
        total_cost = metrics.get("total_cost_usd", 0.0)
        st.metric(
            label="Total Spend",
            value=f"${total_cost:.2f}",
        )
