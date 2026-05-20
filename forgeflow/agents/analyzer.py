"""AnalyzerAgent — scores leads 0-10, flags risks, and determines ICP fit.

Uses structured output so the score is always a validated float, not free text.
"""

from __future__ import annotations

import json
import logging
from typing import cast

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from forgeflow.agents.base import BaseAgent
from forgeflow.state.workflow_state import WorkflowState

logger = logging.getLogger(__name__)

ANALYZER_SYSTEM = """You are the Analyzer Agent for ForgeFlow.

Your job is to score a sales lead and determine whether they are a good fit.

Ideal Customer Profile (ICP) criteria:
- Company size: 50–5000 employees (sweet spot: 200-2000)
- Revenue: $5M–$500M ARR
- Industry: SaaS, FinTech, HealthTech, Enterprise Software, E-Commerce
- Tech-forward: uses cloud, APIs, modern stack
- Growth signals: recent funding, hiring engineering, expanding
- Budget signals: raised Series A or later, or established revenue

Scoring rubric (0-10):
  9-10: Perfect ICP fit, strong buying signals, prioritize immediately
  7-8:  Good fit, worth pursuing with standard proposal
  5-6:  Marginal fit, proceed with lightweight outreach
  3-4:  Weak signals, add to nurture sequence
  0-2:  Clear mismatch, do not pursue

Always explain your scoring with specific evidence from research."""


class QualificationResult(BaseModel):
    score: float = Field(ge=0.0, le=10.0, description="Lead qualification score 0-10")
    qualified: bool = Field(description="True if score >= 4.0")
    icp_fit_reasons: list[str] = Field(description="Why this company fits the ICP")
    risk_flags: list[str] = Field(description="Concerns or red flags")
    recommended_action: str = Field(
        description="One of: 'high_priority', 'standard_proposal', 'nurture', 'disqualify'"
    )
    estimated_deal_value_usd: int = Field(
        description="Estimated annual deal value in USD",
        ge=0,
    )
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in this analysis")


class AnalyzerAgent(BaseAgent):
    def __init__(self, model: BaseChatModel) -> None:
        super().__init__(name="analyzer", model=model, tools=[], system_prompt=ANALYZER_SYSTEM)
        self._structured_model = model.with_structured_output(QualificationResult)

    async def run(self, state: WorkflowState) -> dict:
        self._log_start(state)

        lead_data = state.get("lead_data") or {}
        research_results = state.get("research_results", [])

        # Build research context for the analyzer
        research_text = ""
        for item in research_results:
            if "summary" in item:
                research_text += f"\n\nResearch Summary:\n{item['summary']}"
            elif "result" in item:
                research_text += f"\n\n{item.get('tool', 'Data')}: {str(item['result'])[:500]}"

        prompt = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(
                content=f"Analyze this lead:\n\nCompany: {lead_data.get('company_name')}\n"
                f"Known data: {json.dumps(lead_data, indent=2)}\n"
                f"Research findings:{research_text}\n\n"
                f"Provide a complete qualification analysis."
            ),
        ]

        raw = await self._structured_model.ainvoke(prompt)
        result = cast(QualificationResult, raw)

        logger.info(
            "Analyzer scored lead: %.1f/10 | qualified=%s | action=%s",
            result.score,
            result.qualified,
            result.recommended_action,
        )

        score_dict = result.model_dump()
        score_dict["company"] = lead_data.get("company_name")

        return {
            "analysis_scores": [score_dict],
            "messages": [
                AIMessage(
                    content=(
                        f"[Analyzer] Score: {result.score}/10 | "
                        f"Qualified: {result.qualified} | "
                        f"Action: {result.recommended_action}\n"
                        f"Risk flags: {', '.join(result.risk_flags) or 'None'}"
                    ),
                    name="analyzer",
                )
            ],
        }
