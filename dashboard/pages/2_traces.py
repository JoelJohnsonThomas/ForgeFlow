"""Agent Traces page — Gantt chart visualization of agent execution hops."""

import os

import httpx
import streamlit as st

from dashboard.components.trace_timeline import render_trace_gantt

API_URL = os.environ.get("API_URL", "http://localhost:8000")

st.title("🔍 Agent Execution Traces")


@st.cache_data(ttl=10)
def fetch_runs():
    try:
        return httpx.get(f"{API_URL}/metrics/runs?limit=30", timeout=5).json()
    except Exception:
        return []


@st.cache_data(ttl=5)
def fetch_trace(run_id: str):
    try:
        return httpx.get(f"{API_URL}/workflows/{run_id}/trace", timeout=5).json()
    except Exception:
        return []


runs = fetch_runs()

if not runs:
    st.info("No runs available yet.")
    st.stop()

run_options = {r["run_id"][:8] + "... " + r.get("status", ""): r["run_id"] for r in runs}
selected_label = st.selectbox("Select Run", list(run_options.keys()))
selected_run_id = run_options[selected_label]

traces = fetch_trace(selected_run_id)

if traces:
    st.subheader("Execution Timeline")
    render_trace_gantt(traces)

    st.subheader("Node-by-Node State Changes")
    for trace in traces:
        agent = trace.get("agent_name", "unknown")
        tokens = trace.get("tokens_used", 0)
        cost = float(trace.get("cost_usd", 0))
        error = trace.get("error")

        icon = "❌" if error else "✅"
        with st.expander(f"{icon} {agent.title()} — {tokens} tokens | ${cost:.4f}"):
            if error:
                st.error(error)
            patch = trace.get("output_patch")
            if patch:
                st.json(patch)
            else:
                st.caption("No output patch recorded")
else:
    st.info("No trace records for this run. Traces are written after node completion.")
