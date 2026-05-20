"""Overview page — system health, KPIs, run timeline."""

import os

import httpx
import pandas as pd
import plotly.express as px
import streamlit as st

API_URL = os.environ.get("API_URL", "http://localhost:8000")

st.title("📊 Overview")


@st.cache_data(ttl=10)
def fetch_runs():
    try:
        return httpx.get(f"{API_URL}/metrics/runs?limit=50", timeout=5).json()
    except Exception:
        return []


runs = fetch_runs()

if runs:
    df = pd.DataFrame(runs)
    df["created_at"] = pd.to_datetime(df["created_at"])

    # Status breakdown pie
    col1, col2 = st.columns(2)
    with col1:
        fig = px.pie(
            df,
            names="status",
            title="Run Status Distribution",
            color_discrete_map={
                "completed": "#2ECC71",
                "pending_approval": "#F39C12",
                "running": "#3498DB",
                "failed": "#E74C3C",
            },
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig2 = px.bar(
            df.tail(20),
            x="created_at",
            y="total_cost_usd",
            color="status",
            title="Cost per Run (last 20)",
            labels={"total_cost_usd": "Cost (USD)", "created_at": "Time"},
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("All Runs")
    st.dataframe(df, use_container_width=True)
else:
    st.info("No workflow runs found. Trigger one from the Overview page or the API.")
