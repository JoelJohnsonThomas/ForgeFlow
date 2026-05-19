"""API-level Pydantic request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ------------------------------------------------------------------ #
# Workflow                                                             #
# ------------------------------------------------------------------ #

class WorkflowRunRequest(BaseModel):
    workflow_type: str = "sales_ops"
    lead_data: dict = Field(..., description="Lead input data — must include company_name")
    user_id: str = "anon"
    role: str = "sales_rep"


class WorkflowRunResponse(BaseModel):
    run_id: str
    thread_id: str
    status: str
    message: str = ""


class WorkflowStatusResponse(BaseModel):
    run_id: str
    thread_id: str
    status: str
    current_stage: str
    total_tokens: int
    total_cost_usd: float
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    lead_data: Optional[dict] = None
    proposal: Optional[dict] = None
    analysis_scores: list[dict] = []
    executed_actions: list[str] = []
    errors: list[str] = []


class AgentTraceResponse(BaseModel):
    id: str
    agent_name: str
    stage: str
    started_at: datetime
    completed_at: Optional[datetime]
    tokens_used: int
    cost_usd: float
    error: Optional[str]
    output_patch: Optional[dict]


# ------------------------------------------------------------------ #
# Approvals                                                            #
# ------------------------------------------------------------------ #

class ApprovalRequestResponse(BaseModel):
    id: str
    run_id: str
    token: str
    stage: str
    status: str
    payload: dict
    requested_at: datetime
    expires_at: datetime
    resolved_at: Optional[datetime] = None
    resolution_note: Optional[str] = None


class ApprovalActionRequest(BaseModel):
    note: str = ""
    reason: str = ""


# ------------------------------------------------------------------ #
# Memory                                                               #
# ------------------------------------------------------------------ #

class MemoryStoreRequest(BaseModel):
    content: str = Field(..., min_length=1)
    namespace: str = "default"
    metadata: dict = Field(default_factory=dict)
    ttl_hours: Optional[int] = None


class MemoryStoreResponse(BaseModel):
    memory_id: str


class MemorySearchResult(BaseModel):
    id: str
    content: str
    similarity: float
    namespace: str
    metadata: dict


# ------------------------------------------------------------------ #
# Metrics                                                              #
# ------------------------------------------------------------------ #

class MetricsSummaryResponse(BaseModel):
    total_runs: int
    success_rate: float
    avg_latency_ms: float
    avg_cost_usd: float
    total_cost_usd: float


class EvaluationSummaryResponse(BaseModel):
    avg_faithfulness: float
    avg_relevance: float
    avg_coherence: float
    hallucination_rate: float
    sample_count: int
