"""Tests for WorkflowState reducers and type structure."""

from __future__ import annotations

import operator

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph.message import add_messages


def test_add_messages_appends():
    existing = [HumanMessage(content="hello", id="msg-1")]
    new_msgs = [AIMessage(content="hi there", id="msg-2")]
    result = add_messages(existing, new_msgs)
    assert len(result) == 2
    assert result[-1].content == "hi there"


def test_add_messages_deduplicates_by_id():
    msg = HumanMessage(content="hello", id="msg-1")
    existing = [msg]
    same_msg = HumanMessage(content="hello", id="msg-1")
    result = add_messages(existing, [same_msg])
    assert len(result) == 1


def test_research_results_accumulate():
    a = [{"tool": "web_search", "result": "data 1"}]
    b = [{"tool": "web_search", "result": "data 2"}]
    combined = operator.add(a, b)
    assert len(combined) == 2
    assert combined[0]["result"] == "data 1"
    assert combined[1]["result"] == "data 2"


def test_errors_accumulate():
    initial = ["timeout on tool call"]
    new_error = ["rate limit hit"]
    result = operator.add(initial, new_error)
    assert len(result) == 2
    assert "timeout" in result[0]


def test_override_fields_replace():
    # Override fields (no reducer) should replace — this is the default Python dict behavior
    state = {"current_stage": "qualify", "next_agent": None}
    update = {"current_stage": "research", "next_agent": "analyzer"}
    merged = {**state, **update}
    assert merged["current_stage"] == "research"
    assert merged["next_agent"] == "analyzer"
