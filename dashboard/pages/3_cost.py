"""Cost Analysis page — spending trends by agent and model."""

import os
import httpx
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from forgeflow.config import get_settings

API_URL = os.environ.get("API_URL", "http://localhost:8000")

st.title("💰 Cost Analysis")


@st.cache_data(ttl=30)
def fetch_cost_breakdown(days=7):
    try:
        return httpx.get(f"{API_URL}/metrics/cost?days={days}", timeout=5).json()
    except Exception:
        return []


@st.cache_data(ttl=30)
def fetch_summary():
    try:
        return httpx.get(f"{API_URL}/metrics/", timeout=5).json()
    except Exception:
        return {}


days = st.slider("Days to analyze", 1, 30, 7)
summary = fetch_summary()
cost_data = fetch_cost_breakdown(days)

# Budget gauge
settings = get_settings()
budget = settings.budget_limit_usd
total_cost = summary.get("total_cost_usd", 0.0)

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Spend (30d)", f"${total_cost:.4f}")
with col2:
    st.metric("Budget per Run", f"${budget:.2f}")
with col3:
    st.metric("Avg Cost / Run", f"${summary.get('avg_cost_usd', 0):.4f}")

# Budget gauge
fig_gauge = go.Figure(go.Indicator(
    mode="gauge+number",
    value=total_cost,
    domain={"x": [0, 1], "y": [0, 1]},
    title={"text": "Budget Used ($)"},
    gauge={
        "axis": {"range": [0, budget * 10]},
        "bar": {"color": "#4F8EF7"},
        "steps": [
            {"range": [0, budget * 5], "color": "#2ECC71"},
            {"range": [budget * 5, budget * 8], "color": "#F39C12"},
            {"range": [budget * 8, budget * 10], "color": "#E74C3C"},
        ],
    },
))
st.plotly_chart(fig_gauge, use_container_width=True)

if cost_data:
    df = pd.DataFrame(cost_data)
    if "date" in df.columns and "agent" in df.columns:
        fig = px.bar(
            df,
            x="date",
            y="total_cost_usd",
            color="agent",
            title=f"Daily Cost by Agent (last {days} days)",
            barmode="stack",
        )
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No cost data available yet. Run some workflows to populate this chart.")
