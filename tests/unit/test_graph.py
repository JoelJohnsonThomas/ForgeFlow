"""Tests for graph compilation and conditional edge routing."""

from __future__ import annotations

import pytest

from forgeflow.graph.edges import route_human_approval, route_supervisor


class TestRouteSupervisor:
    def test_routes_to_researcher(self, sample_workflow_state):
        state = {**sample_workflow_state, "next_agent": "researcher"}
        assert route_supervisor(state) == "researcher"

    def test_routes_to_analyzer(self, sample_workflow_state):
        state = {**sample_workflow_state, "next_agent": "analyzer"}
        assert route_supervisor(state) == "analyzer"

    def test_routes_to_executor(self, sample_workflow_state):
        state = {**sample_workflow_state, "next_agent": "executor"}
        assert route_supervisor(state) == "executor"

    def test_routes_to_human_approval(self, sample_workflow_state):
        state = {**sample_workflow_state, "next_agent": "human_approval"}
        assert route_supervisor(state) == "human_approval"

    def test_routes_to_end_on_finish(self, sample_workflow_state):
        state = {**sample_workflow_state, "next_agent": "FINISH"}
        assert route_supervisor(state) == "END"

    def test_routes_to_end_on_none(self, sample_workflow_state):
        state = {**sample_workflow_state, "next_agent": None}
        assert route_supervisor(state) == "END"

    def test_routes_to_end_on_unknown(self, sample_workflow_state):
        state = {**sample_workflow_state, "next_agent": "unknown_agent"}
        assert route_supervisor(state) == "END"


class TestRouteHumanApproval:
    def test_approved_routes_to_executor(self, sample_workflow_state):
        state = {**sample_workflow_state, "approval_status": "approved"}
        assert route_human_approval(state) == "executor"

    def test_rejected_routes_to_end(self, sample_workflow_state):
        state = {**sample_workflow_state, "approval_status": "rejected"}
        assert route_human_approval(state) == "END"

    def test_none_status_routes_to_end(self, sample_workflow_state):
        state = {**sample_workflow_state, "approval_status": None}
        assert route_human_approval(state) == "END"

    def test_unknown_status_routes_to_end(self, sample_workflow_state):
        state = {**sample_workflow_state, "approval_status": "pending"}
        assert route_human_approval(state) == "END"


class TestGraphCompilation:
    @pytest.mark.asyncio
    async def test_compile_graph_no_checkpointer(self):
        """Graph should compile without error in test mode (no DB checkpointer)."""
        from forgeflow.graph.builder import compile_graph

        graph = await compile_graph(mcp_tools=[], use_checkpointer=False)
        assert graph is not None

    @pytest.mark.asyncio
    async def test_graph_has_expected_nodes(self):
        from forgeflow.graph.builder import compile_graph

        graph = await compile_graph(mcp_tools=[], use_checkpointer=False)
        node_names = set(graph.nodes.keys())
        expected = {"supervisor", "researcher", "analyzer", "executor", "human_approval"}
        assert expected.issubset(node_names)
