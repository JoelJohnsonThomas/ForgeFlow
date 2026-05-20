"""Evaluation page — LLM-as-judge scores and hallucination rate."""

import os

import httpx
import plotly.graph_objects as go
import streamlit as st

API_URL = os.environ.get("API_URL", "http://localhost:8000")

st.title("🧪 Evaluation Dashboard")
st.markdown("LLM-as-judge scores across all completed workflow runs.")


@st.cache_data(ttl=30)
def fetch_eval():
    try:
        return httpx.get(f"{API_URL}/metrics/evaluation", timeout=5).json()
    except Exception:
        return {}


eval_data = fetch_eval()

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Faithfulness", f"{eval_data.get('avg_faithfulness', 0):.2f}", help="0-1: grounded in context")
with col2:
    st.metric("Relevance", f"{eval_data.get('avg_relevance', 0):.2f}", help="0-1: answers the query")
with col3:
    st.metric("Coherence", f"{eval_data.get('avg_coherence', 0):.2f}", help="0-1: well-structured")
with col4:
    halluc = eval_data.get("hallucination_rate", 0)
    st.metric("Hallucination Rate", f"{halluc:.1%}", delta=f"{-halluc:.1%}", delta_color="inverse")

# Radar chart
categories = ["Faithfulness", "Relevance", "Coherence"]
values = [
    eval_data.get("avg_faithfulness", 0),
    eval_data.get("avg_relevance", 0),
    eval_data.get("avg_coherence", 0),
]

fig = go.Figure(go.Scatterpolar(
    r=values + [values[0]],
    theta=categories + [categories[0]],
    fill="toself",
    name="Quality Scores",
    line_color="#4F8EF7",
    fillcolor="rgba(79, 142, 247, 0.2)",
))
fig.update_layout(
    polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
    title="Quality Score Radar",
)
st.plotly_chart(fig, use_container_width=True)

sample_count = eval_data.get("sample_count", 0)
st.caption(f"Based on {sample_count} evaluated runs. Scores are computed by GPT-4o-mini acting as judge.")

if sample_count == 0:
    st.info(
        "No evaluation data yet. Run the evaluation suite:\n\n"
        "```bash\npython scripts/run_demo.py\n```"
    )
