"""Finance Reconciliation workflow stages.

Stages (in order):
  ingest         → researcher pulls rows from both ledgers (e.g. bank + ERP)
  match          → analyzer matches entries by amount/date/reference, scores confidence
  flag_variance  → analyzer flags rows that did not match within tolerance
  approve        → graph suspends; human reviews variances above threshold
  post           → executor posts journal entries to close the reconciliation
  done           → workflow complete
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Stage(StrEnum):
    INGEST = "ingest"
    MATCH = "match"
    FLAG_VARIANCE = "flag_variance"
    APPROVE = "approve"
    POST = "post"
    DONE = "done"


@dataclass
class StageConfig:
    name: Stage
    agent: str
    description: str
    next_stages: list[str]
    requires_approval: bool = False


STAGE_CONFIGS: dict[str, StageConfig] = {
    Stage.INGEST: StageConfig(
        name=Stage.INGEST,
        agent="researcher",
        description="Pull rows from source A (bank/processor) and source B (ERP/GL)",
        next_stages=[Stage.MATCH],
    ),
    Stage.MATCH: StageConfig(
        name=Stage.MATCH,
        agent="analyzer",
        description="Pair entries by amount + date + reference; score match confidence",
        next_stages=[Stage.FLAG_VARIANCE],
    ),
    Stage.FLAG_VARIANCE: StageConfig(
        name=Stage.FLAG_VARIANCE,
        agent="analyzer",
        description="Flag unmatched + tolerance-exceeding rows",
        next_stages=[Stage.APPROVE, Stage.POST],
    ),
    Stage.APPROVE: StageConfig(
        name=Stage.APPROVE,
        agent="human_approval",
        description="Human accountant reviews variances above the materiality threshold",
        next_stages=[Stage.POST, Stage.DONE],
        requires_approval=True,
    ),
    Stage.POST: StageConfig(
        name=Stage.POST,
        agent="executor",
        description="Post adjusting journal entries; mark period reconciled",
        next_stages=[Stage.DONE],
    ),
    Stage.DONE: StageConfig(
        name=Stage.DONE,
        agent="supervisor",
        description="Workflow complete",
        next_stages=[],
    ),
}

# A variance below this USD amount can auto-clear; above it requires human approval
MATERIALITY_THRESHOLD_USD = 100.00

# Match tolerance in USD — entries within this delta are considered a match
MATCH_TOLERANCE_USD = 0.05
