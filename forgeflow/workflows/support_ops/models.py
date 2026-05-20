"""Pydantic domain models for the Support Operations workflow."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class TicketChannel(StrEnum):
    EMAIL = "email"
    CHAT = "chat"
    PHONE = "phone"
    PORTAL = "portal"
    SOCIAL = "social"


class TicketStatus(StrEnum):
    NEW = "new"
    INVESTIGATING = "investigating"
    AWAITING_CUSTOMER = "awaiting_customer"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


class TicketInput(BaseModel):
    """Input model for triggering a new support ops workflow."""

    ticket_id: str = Field(..., min_length=1, max_length=64)
    customer_name: str = Field(..., min_length=1, max_length=256)
    customer_email: str | None = None
    subject: str = Field(..., min_length=1, max_length=512)
    body: str = Field(..., min_length=1, max_length=20_000)
    channel: TicketChannel = TicketChannel.EMAIL
    product: str | None = None
    customer_tier: str | None = Field(None, description="free | pro | enterprise")
    previous_ticket_count: int = Field(0, ge=0)

    @field_validator("ticket_id", "subject")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()


class TriageResult(BaseModel):
    """Output of the analyzer stage."""

    severity: int = Field(ge=1, le=5, description="1=trivial, 5=production down")
    category: str = Field(..., description="bug | billing | how-to | feature-request | account")
    customer_sentiment: str = Field(..., description="positive | neutral | frustrated | angry")
    root_cause_hypotheses: list[str]
    needs_human_review: bool
    confidence: float = Field(ge=0.0, le=1.0)


class SupportReply(BaseModel):
    """Drafted reply by the executor stage."""

    reply_id: str
    ticket_id: str
    subject: str
    body: str
    suggested_actions: list[str]
    follow_up_required: bool = False
    status: TicketStatus = TicketStatus.AWAITING_CUSTOMER
