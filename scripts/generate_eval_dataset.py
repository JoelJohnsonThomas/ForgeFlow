"""Generate synthetic eval dataset — prints expected vs actual qualification results."""

from __future__ import annotations

import asyncio
import json

from forgeflow.evaluation.dataset import get_dataset


async def main():
    dataset = get_dataset()
    print(f"ForgeFlow Eval Dataset — {len(dataset)} examples\n")
    print(f"{'ID':<6} {'Company':<25} {'Expected Qualified':<20} {'Score Range'}")
    print("-" * 70)
    for ex in dataset:
        qualified_str = "YES" if ex.expected_qualified else "NO"
        score_range = f"{ex.expected_score_min:.1f} – {ex.expected_score_max:.1f}"
        print(f"{ex.id:<6} {ex.company_name:<25} {qualified_str:<20} {score_range}")

    print(f"\nDataset saved. Run the full eval suite with:")
    print("  python -c \"import asyncio; from forgeflow.evaluation.runner import EvalRunner; ...\"")


if __name__ == "__main__":
    asyncio.run(main())
