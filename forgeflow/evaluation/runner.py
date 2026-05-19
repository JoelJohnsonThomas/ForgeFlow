"""EvalRunner — runs the evaluation suite and aggregates results."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

from forgeflow.evaluation.dataset import EvalExample, get_dataset, get_sample
from forgeflow.evaluation.judge import LLMJudge
from forgeflow.evaluation.metrics import EvalSummary, RunMetrics
from forgeflow.workflows.sales_ops.models import LeadInput
from forgeflow.workflows.sales_ops.pipeline import SalesOpsPipeline

logger = logging.getLogger(__name__)


class EvalRunner:
    def __init__(self, graph, judge: Optional[LLMJudge] = None) -> None:
        self.graph = graph
        self.pipeline = SalesOpsPipeline(graph)
        self.judge = judge or LLMJudge()

    async def run_example(self, example: EvalExample) -> RunMetrics:
        """Run a single eval example and return its metrics."""
        lead_input = LeadInput(company_name=example.company_name)
        start = time.monotonic()
        success = False
        stage_reached = "unknown"
        total_tokens = 0
        total_cost = 0.0
        faithfulness = None
        relevance = None
        coherence = None
        hallucination_flag = None

        try:
            workflow_id, thread_id, final_state = await self.pipeline.run(
                lead_input=lead_input,
                user_id="eval_runner",
                role="sales_rep",
            )

            stage_reached = final_state.get("current_stage", "unknown")
            total_tokens = final_state.get("total_tokens", 0)
            total_cost = final_state.get("total_cost_usd", 0.0)

            scores = final_state.get("analysis_scores", [])
            if scores:
                actual_score = scores[-1].get("score", 0)
                actual_qualified = scores[-1].get("qualified", False)
                success = actual_qualified == example.expected_qualified

            # LLM judge evaluation on the proposal (if generated)
            proposal = final_state.get("proposal")
            if proposal and self.judge:
                try:
                    judge_score = await self.judge.evaluate(
                        input=f"Qualify and propose for {example.company_name}",
                        context=example.description,
                        output=str(proposal.get("executive_summary", "")),
                    )
                    faithfulness = judge_score.faithfulness
                    relevance = judge_score.relevance
                    coherence = judge_score.coherence
                    hallucination_flag = judge_score.hallucination_flag
                except Exception as e:
                    logger.warning("Judge failed for %s: %s", example.id, e)

        except Exception as e:
            logger.error("Eval example %s failed: %s", example.id, e)

        latency_ms = (time.monotonic() - start) * 1000

        return RunMetrics(
            run_id=example.id,
            latency_ms=latency_ms,
            total_tokens=total_tokens,
            total_cost_usd=total_cost,
            success=success,
            stage_reached=stage_reached,
            faithfulness=faithfulness,
            relevance=relevance,
            coherence=coherence,
            hallucination_flag=hallucination_flag,
        )

    async def run_suite(
        self,
        n: Optional[int] = None,
        concurrency: int = 3,
    ) -> EvalSummary:
        """Run the full or partial eval suite with bounded concurrency.

        Args:
            n: Number of examples to evaluate (None = all 20)
            concurrency: Max parallel evaluations
        """
        examples = get_sample(n) if n else get_dataset()
        summary = EvalSummary()

        semaphore = asyncio.Semaphore(concurrency)

        async def run_with_sem(example: EvalExample) -> RunMetrics:
            async with semaphore:
                return await self.run_example(example)

        tasks = [run_with_sem(ex) for ex in examples]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, RunMetrics):
                summary.runs.append(result)
            else:
                logger.error("Eval task failed: %s", result)

        logger.info("Eval suite complete: %s", summary.to_dict())
        return summary
