"""compile_graph() — wires all agents into a LangGraph StateGraph.

Architecture (hub-and-spoke):
  supervisor ──→ researcher ──┐
       ↑          analyzer ──┤
       └──────── executor  ──┘
       └──→ human_approval ──→ executor | END

The supervisor acts as the central router. All workers return to supervisor.
Human approval is an interrupt_before node — graph suspends until resumed via API.
"""

from __future__ import annotations

import logging
import os

from langgraph.graph import END, StateGraph

from forgeflow.agents.analyzer import AnalyzerAgent
from forgeflow.agents.executor import ExecutorAgent
from forgeflow.agents.researcher import ResearcherAgent
from forgeflow.agents.supervisor import SupervisorAgent
from forgeflow.config import get_settings
from forgeflow.graph.checkpointer import get_checkpointer
from forgeflow.graph.edges import route_human_approval, route_supervisor
from forgeflow.graph.nodes import (
    analyzer_node,
    build_node_factory,
    executor_node,
    human_approval_node,
    researcher_node,
    supervisor_node,
)
from forgeflow.models import get_model
from forgeflow.state.workflow_state import WorkflowState

logger = logging.getLogger(__name__)


def _get_domain_prompts(workflow_type: str) -> dict[str, str]:
    """Load prompt overrides for a workflow domain. Returns empty dict for sales_ops (defaults)."""
    if workflow_type == "support_ops":
        from forgeflow.workflows.support_ops import PROMPTS
        return PROMPTS
    if workflow_type == "finance_recon":
        from forgeflow.workflows.finance_recon import PROMPTS
        return PROMPTS
    # sales_ops uses each agent's built-in defaults
    return {}


async def compile_graph(
    mcp_tools: list | None = None,
    use_checkpointer: bool = True,
    workflow_type: str = "sales_ops",
):
    """Build and compile the ForgeFlow StateGraph.

    Args:
        mcp_tools: LangChain-compatible tools from the MCP server adapter.
                   Passed to researcher and executor. If None, agents run
                   without external tools (useful for testing).
        use_checkpointer: If False, compile without persistence (test mode).
        workflow_type: Domain template name — sales_ops (default) | support_ops |
                       finance_recon. Selects per-domain prompts for each agent.

    Returns:
        CompiledStateGraph ready for ainvoke() / astream().
    """
    settings = get_settings()

    # Set LangSmith env vars before any LLM is constructed
    if settings.is_langsmith_enabled():
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key.get_secret_value()
        os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project

    # Models routed through the provider factory — swap via LLM_PROVIDER setting.
    # Supervisor + judge use the strong model; workers use the cheap one.
    model_fast = get_model(strong=False)
    model_strong = get_model(strong=True)
    logger.info(
        "Models built via provider '%s' | workflow_type=%s",
        settings.llm_provider,
        workflow_type,
    )

    # Per-domain prompts — empty dict means "use each agent's built-in default"
    prompts = _get_domain_prompts(workflow_type)

    # Instantiate agents with domain-specific prompts where provided
    supervisor = SupervisorAgent(model=model_strong, system_prompt=prompts.get("supervisor"))
    researcher = ResearcherAgent(
        model=model_fast, tools=mcp_tools or [], system_prompt=prompts.get("researcher")
    )
    analyzer = AnalyzerAgent(model=model_fast, system_prompt=prompts.get("analyzer"))
    executor = ExecutorAgent(
        model=model_fast, tools=mcp_tools or [], system_prompt=prompts.get("executor")
    )

    # Register agents with node functions
    build_node_factory(supervisor, researcher, analyzer, executor)

    # ------------------------------------------------------------------ #
    # Build the graph                                                      #
    # ------------------------------------------------------------------ #
    builder = StateGraph(WorkflowState)

    builder.add_node("supervisor", supervisor_node)
    builder.add_node("researcher", researcher_node)
    builder.add_node("analyzer", analyzer_node)
    builder.add_node("executor", executor_node)
    builder.add_node("human_approval", human_approval_node)

    # Entry point
    builder.set_entry_point("supervisor")

    # Supervisor routes conditionally based on next_agent
    builder.add_conditional_edges(
        "supervisor",
        route_supervisor,
        {
            "researcher": "researcher",
            "analyzer": "analyzer",
            "executor": "executor",
            "human_approval": "human_approval",
            "END": END,
        },
    )

    # All workers return to supervisor (hub-and-spoke)
    builder.add_edge("researcher", "supervisor")
    builder.add_edge("analyzer", "supervisor")
    builder.add_edge("executor", "supervisor")

    # Human approval routes to executor (approved) or END (rejected)
    builder.add_conditional_edges(
        "human_approval",
        route_human_approval,
        {"executor": "executor", "END": END},
    )

    # ------------------------------------------------------------------ #
    # Compile with PostgreSQL checkpointer + human-in-the-loop interrupt  #
    # ------------------------------------------------------------------ #
    compile_kwargs: dict = {
        "interrupt_before": ["human_approval"],
    }

    if use_checkpointer:
        compile_kwargs["checkpointer"] = await get_checkpointer()

    graph = builder.compile(**compile_kwargs)

    logger.info("ForgeFlow graph compiled | nodes=%s", list(builder.nodes))
    return graph
