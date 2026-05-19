"""ResearcherAgent — gathers company intelligence using MCP tools + semantic memory.

Uses a ReAct-style loop: the LLM decides which tools to call, tools execute
via the MCP client adapter, results accumulate in research_results.
"""

from __future__ import annotations

import json
import logging

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage, ToolMessage
from langchain_core.tools import BaseTool

from forgeflow.agents.base import BaseAgent
from forgeflow.state.workflow_state import WorkflowState

logger = logging.getLogger(__name__)

RESEARCHER_SYSTEM = """You are the Researcher Agent for ForgeFlow.

Your mission: gather comprehensive intelligence about a sales lead's company.

Use the available tools to find:
1. Company funding history, investors, and valuation
2. Employee count and recent growth
3. Revenue estimates and business model
4. Technology stack (from job listings or company website)
5. Recent news, press releases, or announcements
6. Key decision makers and their LinkedIn profiles

Be thorough. Use multiple searches with different queries.
Compile all findings in a structured summary.
When done, output a JSON summary with keys:
  company_name, funding_total, employees, revenue_estimate,
  tech_stack, key_news, decision_makers, icp_signals"""

MAX_TOOL_ITERATIONS = 5


class ResearcherAgent(BaseAgent):
    def __init__(self, model: BaseChatModel, tools: list[BaseTool]) -> None:
        super().__init__(
            name="researcher",
            model=model,
            tools=tools,
            system_prompt=RESEARCHER_SYSTEM,
        )
        self._tool_map = {t.name: t for t in tools}

    async def run(self, state: WorkflowState) -> dict:
        self._log_start(state)

        lead_data = state.get("lead_data") or {}
        company_name = lead_data.get("company_name", "Unknown Company")

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(
                content=f"Research this company for lead qualification:\n\n"
                f"Company: {company_name}\n"
                f"Known info: {json.dumps(lead_data, indent=2)}\n\n"
                f"Use the search tools to gather intelligence."
            ),
        ]

        research_findings: list[dict] = []
        total_tokens = 0

        # ReAct loop — LLM calls tools until it decides to stop
        for iteration in range(MAX_TOOL_ITERATIONS):
            response = await self.model.ainvoke(messages)
            messages.append(response)

            # Count tokens if usage metadata is available
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                total_tokens += response.usage_metadata.get("total_tokens", 0)

            # No more tool calls — LLM is done
            if not response.tool_calls:
                break

            # Execute each tool call
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_id = tool_call["id"]

                tool = self._tool_map.get(tool_name)
                if not tool:
                    result = f"Tool '{tool_name}' not found"
                    logger.warning("ResearcherAgent: unknown tool '%s'", tool_name)
                else:
                    try:
                        result = await tool.ainvoke(tool_args)
                        research_findings.append({
                            "tool": tool_name,
                            "query": tool_args,
                            "result": result,
                            "iteration": iteration,
                        })
                    except Exception as e:
                        result = f"Tool error: {e}"
                        logger.error("Tool '%s' failed: %s", tool_name, e)

                messages.append(
                    ToolMessage(content=str(result), tool_call_id=tool_id)
                )

        # Extract the final summary from the last AI message
        final_summary = ""
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and not msg.tool_calls:
                final_summary = msg.content
                break

        self._log_finish(total_tokens, 0.0)

        return {
            "research_results": research_findings + [
                {"summary": final_summary, "company": company_name}
            ],
            "messages": [
                AIMessage(
                    content=f"[Researcher] Completed research on {company_name}. "
                    f"Found {len(research_findings)} data points.",
                    name="researcher",
                )
            ],
            "total_tokens": state.get("total_tokens", 0) + total_tokens,
        }
