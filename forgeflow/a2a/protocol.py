"""A2A Protocol data models — based on Google's Agent2Agent open standard (2025).

Implements JSON-RPC 2.0 envelope with:
  - AgentCard: agent identity + capability advertisement
  - A2ATask: work unit delegated from one agent to another
  - A2AArtifact: result or output produced by a task
  - A2AMessage: JSON-RPC 2.0 envelope wrapping tasks and artifacts

Reference: https://a2a-protocol.org/latest/specification/
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class TaskState(StrEnum):
    SUBMITTED = "submitted"
    WORKING = "working"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class ArtifactType(StrEnum):
    TEXT = "text"
    DATA = "data"
    FILE = "file"
    ERROR = "error"


class AgentCard(BaseModel):
    """Describes an agent's identity and capabilities for discovery."""

    agent_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    capabilities: list[str] = Field(description="Skill tags e.g. ['web_search', 'lead_scoring']")
    endpoint: str = Field(description="URL or identifier where this agent can receive tasks")
    version: str = "1.0.0"
    metadata: dict[str, Any] = Field(default_factory=dict)


class A2ATask(BaseModel):
    """A unit of work delegated from one agent to another."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sender_id: str
    receiver_id: str
    method: str = Field(description="The action requested e.g. 'research_company'")
    params: dict[str, Any] = Field(default_factory=dict)
    state: TaskState = TaskState.SUBMITTED
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    timeout_seconds: int = 300

    def mark_working(self) -> None:
        self.state = TaskState.WORKING
        self.updated_at = datetime.now(UTC)

    def mark_completed(self) -> None:
        self.state = TaskState.COMPLETED
        self.updated_at = datetime.now(UTC)

    def mark_failed(self) -> None:
        self.state = TaskState.FAILED
        self.updated_at = datetime.now(UTC)


class A2AArtifact(BaseModel):
    """Output produced by a completed A2A task."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str
    artifact_type: ArtifactType = ArtifactType.DATA
    content: str | dict | list
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class A2AMessage(BaseModel):
    """JSON-RPC 2.0 envelope for agent-to-agent communication."""

    jsonrpc: str = "2.0"
    method: str
    params: dict[str, Any] = Field(default_factory=dict)
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    @classmethod
    def task_request(cls, task: A2ATask) -> A2AMessage:
        return cls(
            method="tasks/send",
            params={"task": task.model_dump(mode="json")},
        )

    @classmethod
    def artifact_response(cls, artifact: A2AArtifact, request_id: str) -> A2AMessage:
        return cls(
            method="artifacts/send",
            params={"artifact": artifact.model_dump(mode="json")},
            id=request_id,
        )
