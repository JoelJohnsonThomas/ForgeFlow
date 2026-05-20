"""Audit Log Search page — query the immutable audit trail.

Compliance teams need to answer questions like:
  - "Who triggered workflow X?"
  - "What did role=manager touch last week?"
  - "Which requests were denied?"

This page fronts the /audit/search endpoint with simple filters.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta

import httpx
import pandas as pd
import streamlit as st

API_URL = os.environ.get("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Audit Log", page_icon=":mag:", layout="wide")
st.title("Audit Log Search")

# --- Top-of-page summary ---
with st.spinner("Loading audit stats..."):
    try:
        stats_resp = httpx.get(f"{API_URL}/audit/stats", params={"days": 7}, timeout=10.0)
        stats = stats_resp.json() if stats_resp.status_code == 200 else {}
    except Exception as exc:
        st.error(f"Could not load audit stats: {exc}")
        stats = {}

c1, c2, c3, c4 = st.columns(4)
c1.metric("Requests (7d)", stats.get("total", 0))
c2.metric("Denied", stats.get("denied", 0))
c3.metric("Errors", stats.get("errors", 0))
c4.metric("Distinct users", stats.get("distinct_users", 0))

if stats.get("top_resources"):
    with st.expander("Top resources (last 7 days)"):
        st.dataframe(
            pd.DataFrame(stats["top_resources"]),
            use_container_width=True,
            hide_index=True,
        )

st.divider()

# --- Filters ---
st.subheader("Search")
fc1, fc2, fc3 = st.columns(3)
with fc1:
    user_id = st.text_input("User ID", "")
    role = st.selectbox("Role", ["", "admin", "manager", "sales_rep", "viewer", "anonymous"])
with fc2:
    action = st.selectbox("HTTP method", ["", "GET", "POST", "PUT", "PATCH", "DELETE"])
    outcome = st.selectbox("Outcome", ["", "allowed", "denied", "error"])
with fc3:
    resource = st.text_input("Resource path contains", "")
    days_back = st.slider("Within last N days", 1, 30, 7)

since = (datetime.utcnow() - timedelta(days=days_back)).isoformat()

params = {
    "since": since,
    "limit": 200,
}
if user_id:
    params["user_id"] = user_id
if role:
    params["role"] = role
if action:
    params["action"] = action
if resource:
    params["resource"] = resource
if outcome:
    params["outcome"] = outcome

# --- Results ---
if st.button("Search", type="primary"):
    with st.spinner("Searching audit log..."):
        try:
            resp = httpx.get(f"{API_URL}/audit/search", params=params, timeout=15.0)
            data = resp.json() if resp.status_code == 200 else {}
        except Exception as exc:
            st.error(f"Search failed: {exc}")
            data = {}

    total = data.get("total", 0)
    items = data.get("items", [])
    st.caption(f"Found {total} matching entries (showing first {len(items)})")

    if items:
        df = pd.DataFrame(items)
        st.dataframe(
            df[
                [
                    "timestamp",
                    "user_id",
                    "role",
                    "action",
                    "resource",
                    "outcome",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

        with st.expander("Raw JSON of one entry (for forensic detail)"):
            st.json(items[0])
    else:
        st.info("No matching audit entries.")
