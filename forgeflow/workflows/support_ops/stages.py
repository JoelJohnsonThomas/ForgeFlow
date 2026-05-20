"""Support Ops workflow stages.

Stages (in order):
  triage       → researcher gathers ticket context + knowledge base hits
  investigate  → analyzer classifies severity, identifies root cause hypotheses
  respond      → executor drafts response
  escalate     → graph suspends for human review (high severity / unhappy customer)
  resolve      → executor sends reply, updates ticket status
  done         → workflow complete
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Stage(StrEnum):
    TRIAGE = "triage"
    INVESTIGATE = "investigate"
    RESPOND = "respond"
    ESCALATE = "escalate"
    RESOLVE = "resolve"
    DONE = "done"


@dataclass
class StageConfig:
    name: Stage
    agent: str
    description: str
    next_stages: list[str]
    requires_approval: bool = False


STAGE_CONFIGS: dict[str, StageConfig] = {
    Stage.TRIAGE: StageConfig(
        name=Stage.TRIAGE,
        agent="researcher",
        description="Gather ticket history + relevant knowledge base articles",
        next_stages=[Stage.INVESTIGATE],
    ),
    Stage.INVESTIGATE: StageConfig(
        name=Stage.INVESTIGATE,
        agent="analyzer",
        description="Classify severity 1-5, identify root cause hypotheses",
        next_stages=[Stage.RESPOND, Stage.ESCALATE],
    ),
    Stage.RESPOND: StageConfig(
        name=Stage.RESPOND,
        agent="executor",
        description="Draft a customer-facing reply",
        next_stages=[Stage.ESCALATE, Stage.RESOLVE],
    ),
    Stage.ESCALATE: StageConfig(
        name=Stage.ESCALATE,
        agent="human_approval",
        description="Human reviews before reply is sent (high-severity / billing / churn-risk)",
        next_stages=[Stage.RESOLVE, Stage.DONE],
        requires_approval=True,
    ),
    Stage.RESOLVE: StageConfig(
        name=Stage.RESOLVE,
        agent="executor",
        description="Send the reply, update ticket status",
        next_stages=[Stage.DONE],
    ),
    Stage.DONE: StageConfig(
        name=Stage.DONE,
        agent="supervisor",
        description="Workflow complete",
        next_stages=[],
    ),
}

# Severity at which we always escalate to a human reviewer
ESCALATION_SEVERITY_THRESHOLD = 4
