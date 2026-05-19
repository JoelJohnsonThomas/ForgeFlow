"""ForgeFlow Streamlit Dashboard — entry point.

Run with:
  streamlit run dashboard/app.py

Pages are in dashboard/pages/ and loaded automatically by Streamlit's multi-page app.
"""

import os
import streamlit as st
import httpx

from dashboard.components.sidebar import render_sidebar
from dashboard.components.metric_cards import render_kpi_row

API_URL = os.environ.get("API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="ForgeFlow — AI Observability",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Sidebar (shared across all pages)
filters = render_sidebar()

# Overview page content
st.title("⚡ ForgeFlow — Multi-Agent Orchestrator")
st.markdown(
    "Real-time observability for enterprise AI sales operations workflows. "
    "**LangGraph + MCP + A2A + PGVector**"
)
st.divider()


@st.cache_data(ttl=10)
def fetch_metrics():
    try:
        resp = httpx.get(f"{API_URL}/metrics/", timeout=5)
        return resp.json()
    except Exception:
        return {}


@st.cache_data(ttl=10)
def fetch_recent_runs():
    try:
        resp = httpx.get(f"{API_URL}/metrics/runs?limit=20", timeout=5)
        return resp.json()
    except Exception:
        return []


metrics = fetch_metrics()
runs = fetch_recent_runs()

# KPI cards
render_kpi_row(metrics)
st.divider()

# Recent runs table
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Recent Workflow Runs")
    if runs:
        import pandas as pd
        df = pd.DataFrame(runs)
        st.dataframe(
            df[["run_id", "workflow_type", "status", "total_tokens", "total_cost_usd", "created_at"]],
            use_container_width=True,
        )
    else:
        st.info("No runs yet. Trigger one via the API or the demo script.")

with col2:
    st.subheader("Quick Actions")
    company = st.text_input("Company Name", placeholder="e.g. Stripe")
    if st.button("🚀 Trigger Workflow", use_container_width=True, type="primary"):
        if company:
            with st.spinner("Running workflow..."):
                try:
                    resp = httpx.post(
                        f"{API_URL}/workflows/run",
                        json={"lead_data": {"company_name": company}},
                        headers={"X-Role": "sales_rep", "X-User-Id": "dashboard"},
                        timeout=120,
                    )
                    result = resp.json()
                    st.success(f"Run started! ID: {result.get('run_id', '')[:8]}...")
                    st.cache_data.clear()
                except Exception as e:
                    st.error(f"Failed: {e}")
        else:
            st.warning("Enter a company name first.")

    st.subheader("Pending Approvals")
    try:
        pending = httpx.get(
            f"{API_URL}/approvals/pending",
            headers={"X-Role": "manager"},
            timeout=5,
        ).json()
        if pending:
            for item in pending[:3]:
                with st.expander(f"🔔 {item.get('stage', 'proposal')} approval"):
                    st.json(item.get("payload", {}))
                    token = item.get("token", "")
                    if st.button(f"✅ Approve", key=f"approve_{token}"):
                        httpx.post(
                            f"{API_URL}/approvals/{token}/approve",
                            json={"note": "Approved via dashboard"},
                            headers={"X-Role": "manager"},
                            timeout=10,
                        )
                        st.rerun()
        else:
            st.caption("No pending approvals.")
    except Exception:
        st.caption("Approvals unavailable.")
