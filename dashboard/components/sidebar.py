"""Shared sidebar component — navigation + filters."""

from __future__ import annotations

from datetime import datetime, timedelta

import streamlit as st


def render_sidebar() -> dict:
    """Render the sidebar and return filter state."""
    with st.sidebar:
        st.image("https://via.placeholder.com/180x40?text=ForgeFlow", use_column_width=True)
        st.markdown("**Multi-Agent Enterprise AI**")
        st.divider()

        st.markdown("### Navigation")
        st.page_link("dashboard/app.py", label="Overview", icon="📊")
        st.page_link("dashboard/pages/2_traces.py", label="Agent Traces", icon="🔍")
        st.page_link("dashboard/pages/3_cost.py", label="Cost Analysis", icon="💰")
        st.page_link("dashboard/pages/4_evaluation.py", label="Evaluation", icon="🧪")

        st.divider()
        st.markdown("### Filters")

        days_back = st.slider("Days back", 1, 30, 7)
        start_date = datetime.now() - timedelta(days=days_back)

        workflow_filter = st.selectbox(
            "Workflow type",
            ["All", "sales_ops"],
            index=0,
        )

        status_filter = st.multiselect(
            "Status",
            ["completed", "running", "pending_approval", "failed"],
            default=["completed", "running", "pending_approval"],
        )

        st.divider()
        if st.button("🔄 Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    return {
        "start_date": start_date,
        "workflow_filter": None if workflow_filter == "All" else workflow_filter,
        "status_filter": status_filter,
    }
