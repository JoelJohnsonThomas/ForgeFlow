"""RBAC domain models."""

from __future__ import annotations

from pydantic import BaseModel


class Role(BaseModel):
    name: str
    description: str
    permissions: list[str]  # "action:resource" strings


class Permission(BaseModel):
    action: str
    resource: str

    def key(self) -> str:
        return f"{self.action}:{self.resource}"


class UserContext(BaseModel):
    user_id: str
    role: str
    email: str | None = None
