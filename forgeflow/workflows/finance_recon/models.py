"""Pydantic domain models for the Finance Reconciliation workflow."""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class LedgerSource(StrEnum):
    BANK = "bank"
    ERP = "erp"
    PAYMENT_PROCESSOR = "payment_processor"
    GL = "general_ledger"
    SUBLEDGER = "subledger"


class VarianceDisposition(StrEnum):
    AUTO_CLEARED = "auto_cleared"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class ReconciliationInput(BaseModel):
    """Input model for triggering a new finance reconciliation workflow."""

    period_label: str = Field(..., min_length=1, max_length=64, description="e.g. '2026-04'")
    source_a: LedgerSource = Field(..., description="Authoritative ledger (e.g. bank)")
    source_b: LedgerSource = Field(..., description="Comparison ledger (e.g. ERP)")
    period_start: date
    period_end: date
    materiality_threshold_usd: float = Field(100.0, ge=0.0)
    entity: str | None = Field(None, max_length=128, description="Legal entity / business unit")

    @field_validator("period_label")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()


class LedgerEntry(BaseModel):
    entry_id: str
    posted_on: date
    amount_usd: float
    reference: str | None = None
    description: str | None = None
    source: LedgerSource


class MatchResult(BaseModel):
    """One paired (or unpaired) entry produced by the analyzer."""

    source_a_entry: LedgerEntry | None
    source_b_entry: LedgerEntry | None
    delta_usd: float = Field(description="A.amount - B.amount; 0 = perfect match")
    confidence: float = Field(ge=0.0, le=1.0)
    is_matched: bool
    notes: str | None = None


class Variance(BaseModel):
    """A reconciliation difference that needs to be cleared."""

    variance_id: str
    delta_usd: float
    direction: str = Field(..., description="positive | negative")
    suspected_cause: str
    material: bool = Field(description="True if abs(delta) >= materiality threshold")
    disposition: VarianceDisposition = VarianceDisposition.PENDING_REVIEW


class ReconciliationReport(BaseModel):
    """Final output of the reconciliation workflow."""

    report_id: str
    period_label: str
    matched_count: int = Field(ge=0)
    unmatched_count: int = Field(ge=0)
    total_variance_usd: float
    material_variances: list[Variance]
    auto_cleared_variances: list[Variance]
    status: str = "draft"
