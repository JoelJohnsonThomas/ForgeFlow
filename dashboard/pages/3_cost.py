"""Cost Analysis page — spending trends, budget alerts, drill-downs."""

import os

import httpx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from forgeflow.config import get_settings

API_URL = os.environ.get("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Cost Analysis", layout="wide")
st.title("Cost Analysis")


@st.cache_data(ttl=30)
def _get(path: str, params: dict | None = None):
    try:
        return httpx.get(f"{API_URL}{path}", params=params or {}, timeout=8).json()
    except Exception as exc:
        st.warning(f"Could not fetch {path}: {exc}")
        return None


days = st.slider("Days to analyze", 1, 30, 7)

summary = _get("/metrics/") or {}
by_agent = _get("/metrics/cost", {"days": days}) or []
by_type = _get("/metrics/cost/by_workflow_type", {"days": days}) or []
top_runs = _get("/metrics/cost/top_runs", {"days": days, "limit": 10}) or []
alerts = _get("/metrics/cost/alerts", {"days": days}) or []

settings = get_settings()
budget = settings.budget_limit_usd
total_cost = float(summary.get("total_cost_usd", 0.0))

# --- KPI strip ---
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total spend (30d)", f"${total_cost:.4f}")
c2.metric("Per-run budget", f"${budget:.2f}")
c3.metric("Avg cost / run", f"${summary.get('avg_cost_usd', 0):.4f}")
c4.metric("Budget alerts", len(alerts))

# --- Budget alerts strip ---
if alerts:
    exceeded = [a for a in alerts if a.get("severity") == "exceeded"]
    warnings = [a for a in alerts if a.get("severity") == "warning"]
    if exceeded:
        st.error(
            f"{len(exceeded)} workflow run(s) hit or exceeded the per-run budget "
            f"of ${budget:.2f}. See drill-down below."
        )
    if warnings:
        st.warning(
            f"{len(warnings)} workflow run(s) used >=90% of the per-run budget."
        )
else:
    st.success("No budget alerts in the selected window.")

# --- Budget utilization gauge ---
gauge_max = max(budget * 10, total_cost * 1.1, 0.01)
fig_gauge = go.Figure(
    go.Indicator(
        mode="gauge+number",
        value=total_cost,
        domain={"x": [0, 1], "y": [0, 1]},
        title={"text": "Cumulative spend ($)"},
        gauge={
            "axis": {"range": [0, gauge_max]},
            "bar": {"color": "#4F8EF7"},
            "steps": [
                {"range": [0, budget * 5], "color": "#2ECC71"},
                {"range": [budget * 5, budget * 8], "color": "#F39C12"},
                {"range": [budget * 8, gauge_max], "color": "#E74C3C"},
            ],
        },
    )
)
st.plotly_chart(fig_gauge, use_container_width=True)

# --- Two-column: by agent + by workflow_type ---
left, right = st.columns(2)

with left:
    st.subheader("By agent")
    if by_agent:
        df = pd.DataFrame(by_agent)
        if "date" in df.columns and "agent" in df.columns:
            fig = px.bar(
                df,
                x="date",
                y="total_cost_usd",
                color="agent",
                title=f"Daily cost by agent (last {days}d)",
                barmode="stack",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Per-agent breakdown not yet populated.")
    else:
        st.info("No data.")

with right:
    st.subheader("By workflow type")
    if by_type:
        df_t = pd.DataFrame(by_type)
        if "date" in df_t.columns and "workflow_type" in df_t.columns:
            fig_t = px.bar(
                df_t,
                x="date",
                y="total_cost_usd",
                color="workflow_type",
                title=f"Daily cost by workflow type (last {days}d)",
                barmode="stack",
            )
            st.plotly_chart(fig_t, use_container_width=True)

            with st.expander("Cost-per-1k-tokens (efficiency)"):
                agg = (
                    df_t.groupby("workflow_type")[["total_cost_usd", "total_tokens"]]
                    .sum()
                    .reset_index()
                )
                agg["cost_per_1k_tokens"] = (
                    agg["total_cost_usd"] / agg["total_tokens"].clip(lower=1) * 1000
                )
                st.dataframe(agg, use_container_width=True, hide_index=True)
        else:
            st.info("Per-workflow breakdown not yet populated.")
    else:
        st.info("No data.")

st.divider()

# --- Top expensive runs ---
st.subheader("Most expensive recent runs")
if top_runs:
    df_top = pd.DataFrame(top_runs)
    st.dataframe(
        df_top,
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No completed runs in the selected window.")
