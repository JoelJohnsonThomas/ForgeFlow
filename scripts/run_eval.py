"""Run the evaluation suite and write results to a JSON file.

Usage:
    python scripts/run_eval.py --n 5 --output eval_results.json
    python scripts/run_eval.py --check-regression --baseline tests/eval_baseline.json

The --check-regression flag runs the regression checker against the committed
baseline and exits 1 if any metric regressed beyond tolerance. CI uses this
mode to fail PRs that ship quality regressions.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

from forgeflow.evaluation.regression import check
from forgeflow.evaluation.runner import EvalRunner
from forgeflow.graph.builder import compile_graph

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


async def _main(n: int, output: Path | None, baseline: Path | None) -> int:
    # Compile graph WITHOUT the postgres checkpointer — eval should run independently
    graph = await compile_graph(mcp_tools=[], use_checkpointer=False)

    runner = EvalRunner(graph)
    logger.info("Running eval suite with n=%d", n)
    summary = await runner.run_suite(n=n)

    results = summary.to_dict()
    print(json.dumps(results, indent=2))  # noqa: T201

    if output:
        output.write_text(json.dumps(results, indent=2) + "\n")
        logger.info("Wrote eval results to %s", output)

    if baseline:
        report = check(summary, baseline)
        print("\nRegression report:")  # noqa: T201
        for f in report.findings:
            marker = {"ok": "OK", "warning": "WARN", "regression": "FAIL"}[f.severity]
            print(  # noqa: T201
                f"  [{marker}] {f.metric}: current={f.current:.4f} "
                f"baseline={f.baseline:.4f} — {f.explanation}"
            )
        if not report.passed:
            logger.error("Eval regression check FAILED")
            return 1
        logger.info("Eval regression check passed")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the ForgeFlow evaluation suite")
    parser.add_argument("--n", type=int, default=5, help="Number of examples (default: 5)")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write summary JSON to this path",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=None,
        help="Compare to baseline; exit 1 on regression",
    )
    args = parser.parse_args()

    return asyncio.run(_main(args.n, args.output, args.baseline))


if __name__ == "__main__":
    sys.exit(main())
