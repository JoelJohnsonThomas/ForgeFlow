"""Marketplace — browse built-in + community workflow templates."""

from __future__ import annotations

import os

import httpx
import pandas as pd
import streamlit as st

API_URL = os.environ.get("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Marketplace", layout="wide")
st.title("Workflow Marketplace")

st.caption(
    "Browse the workflow templates installed in this deployment. "
    "Drop a manifest under `templates/community/` to add your own."
)


@st.cache_data(ttl=30)
def _fetch(params: dict | None = None) -> dict:
    try:
        return httpx.get(
            f"{API_URL}/marketplace/templates",
            params=params or {},
            timeout=8.0,
        ).json()
    except Exception as exc:
        st.error(f"Could not reach marketplace API: {exc}")
        return {"total": 0, "templates": []}


# Filters
c1, c2, _ = st.columns([1, 1, 2])
with c1:
    domain = st.selectbox(
        "Domain",
        ["", "sales_ops", "support_ops", "finance_recon", "custom"],
    )
with c2:
    tag = st.text_input("Tag contains", "")

params: dict = {}
if domain:
    params["domain"] = domain
if tag:
    params["tag"] = tag

data = _fetch(params)
templates = data.get("templates", [])

st.metric("Templates available", data.get("total", 0))

if not templates:
    st.info("No templates match the current filters.")
else:
    df = pd.DataFrame(templates)[
        ["name", "version", "domain", "author", "description"]
    ]
    st.dataframe(df, use_container_width=True, hide_index=True)

    with st.expander("Inspect a template"):
        names = [t["name"] for t in templates]
        chosen = st.selectbox("Template", names)
        match = next((t for t in templates if t["name"] == chosen), None)
        if match:
            st.json(match)
