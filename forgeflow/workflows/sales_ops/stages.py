"""Sales Ops workflow stage definitions and transition logic.

Stages (in order):
  qualify   → researcher gathers company intelligence
  research  → analyzer scores the lead
  analyze   → executor drafts proposal (if score >= 4.0) OR disqualifies
  propose   → graph suspends for human approval
  approve   → executor sends email + updates CRM
  execute   → final stage
  done      → workflow complete
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Stage(StrEnum):
    QUALIFY = "qualify"
    RESEARCH = "research"
    ANALYZE = "analyze"
    PROPOSE = "propose"
    APPROVE = "approve"
    EXECUTE = "execute"
    DONE = "done"


@dataclass
class StageConfig:
    name: Stage
    agent: str              # Which agent handles this stage
    description: str
    next_stages: list[str]  # Possible next stages after this one
    requires_approval: bool = False


STAGE_CONFIGS: dict[str, StageConfig] = {
    Stage.QUALIFY: StageConfig(
        name=Stage.QUALIFY,
        agent="researcher",
        description="Gather company intelligence: funding, size, tech stack, recent news",
        next_stages=[Stage.RESEARCH],
    ),
    Stage.RESEARCH: StageConfig(
        name=Stage.RESEARCH,
        agent="analyzer",
        description="Score lead 0-10, determine ICP fit, flag risks",
        next_stages=[Stage.ANALYZE],
    ),
    Stage.ANALYZE: StageConfig(
        name=Stage.ANALYZE,
        agent="executor",
        description="Draft proposal if score >= 4.0, else disqualify",
        next_stages=[Stage.PROPOSE, Stage.DONE],
    ),
    Stage.PROPOSE: StageConfig(
        name=Stage.PROPOSE,
        agent="human_approval",
        description="Suspend workflow — human manager reviews proposal",
        next_stages=[Stage.APPROVE, Stage.DONE],
        requires_approval=True,
    ),
    Stage.APPROVE: StageConfig(
        name=Stage.APPROVE,
        agent="executor",
        description="Execute: send email, update CRM, log outcome",
        next_stages=[Stage.EXECUTE],
    ),
    Stage.EXECUTE: StageConfig(
        name=Stage.EXECUTE,
        agent="executor",
        description="Final execution phase",
        next_stages=[Stage.DONE],
    ),
    Stage.DONE: StageConfig(
        name=Stage.DONE,
        agent="supervisor",
        description="Workflow complete",
        next_stages=[],
    ),
}

DISQUALIFICATION_THRESHOLD = 4.0  # Score below this → disqualify
HIGH_PRIORITY_THRESHOLD = 8.0     # Score above this → fast-track
