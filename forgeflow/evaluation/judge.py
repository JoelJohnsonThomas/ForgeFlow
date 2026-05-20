"""LLM-as-judge evaluation — scores agent outputs on faithfulness, relevance, coherence."""

from __future__ import annotations

import logging

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from forgeflow.config import get_settings
from forgeflow.workflows.sales_ops.prompts import JUDGE_EVALUATION_PROMPT

logger = logging.getLogger(__name__)


class JudgeScore(BaseModel):
    faithfulness: float = Field(ge=0.0, le=1.0)
    relevance: float = Field(ge=0.0, le=1.0)
    coherence: float = Field(ge=0.0, le=1.0)
    hallucination_flag: bool

    @property
    def overall(self) -> float:
        return (self.faithfulness + self.relevance + self.coherence) / 3

    @property
    def hallucination_penalty(self) -> float:
        return -0.3 if self.hallucination_flag else 0.0

    @property
    def adjusted_score(self) -> float:
        return max(0.0, self.overall + self.hallucination_penalty)


class LLMJudge:
    """Evaluates agent outputs using a separate LLM call with structured output."""

    def __init__(self) -> None:
        settings = get_settings()
        model = ChatOpenAI(
            model=settings.openai_model_strong,
            api_key=settings.openai_api_key.get_secret_value(),
            temperature=0,
        )
        self._model = model.with_structured_output(JudgeScore)

    async def evaluate(
        self,
        input: str,
        context: str,
        output: str,
    ) -> JudgeScore:
        """Score an agent's output against its input and context.

        Args:
            input: What the agent was asked to do
            context: Information the agent had access to
            output: What the agent produced

        Returns:
            JudgeScore with faithfulness, relevance, coherence, hallucination_flag
        """
        prompt = JUDGE_EVALUATION_PROMPT.format(
            input=input[:2000],
            context=context[:3000],
            output=output[:2000],
        )

        try:
            score: JudgeScore = await self._model.ainvoke(prompt)
            logger.debug(
                "Judge score: faithful=%.2f rel=%.2f coh=%.2f hallucination=%s",
                score.faithfulness,
                score.relevance,
                score.coherence,
                score.hallucination_flag,
            )
            return score
        except Exception as e:
            logger.error("LLM judge evaluation failed: %s", e)
            # Return a neutral score on failure — don't crash the eval
            return JudgeScore(
                faithfulness=0.5,
                relevance=0.5,
                coherence=0.5,
                hallucination_flag=False,
            )
