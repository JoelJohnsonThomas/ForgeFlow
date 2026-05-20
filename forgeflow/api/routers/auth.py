"""Auth routes — JWT issuance for testing and demo flows.

Production note: this `/auth/login` endpoint is a stub that issues tokens
from a static user table. Replace with your real identity provider (OIDC,
SAML, an LDAP bind, etc.) before deploying — the JWT shape produced here
is stable so the rest of the app keeps working.

Open path: not RBAC-gated (see _OPEN_PREFIXES in middleware/auth.py).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from forgeflow.auth.jwt import JWTError, create_access_token, decode_access_token

logger = logging.getLogger(__name__)
router = APIRouter()


class LoginRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=128)
    role: str = Field(..., description="admin | manager | sales_rep | viewer")
    workspace_id: str | None = None
    ttl_hours: int = Field(24, ge=1, le=24 * 30)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    role: str
    workspace_id: str | None = None


# Demo / dev users. Replace with a real identity store in production.
_DEMO_USERS = {
    "admin": "admin",
    "manager-1": "manager",
    "rep-1": "sales_rep",
    "viewer-1": "viewer",
}


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest) -> TokenResponse:
    """Issue a JWT for a known user_id with their pre-configured role.

    The request's role field is ignored if user_id is in the demo store —
    the stored role wins (defense against role escalation via request body).
    """
    expected_role = _DEMO_USERS.get(req.user_id)
    if expected_role is None:
        raise HTTPException(status_code=401, detail=f"unknown user_id '{req.user_id}'")

    token = create_access_token(
        user_id=req.user_id,
        role=expected_role,
        workspace_id=req.workspace_id,
        ttl_hours=req.ttl_hours,
    )
    return TokenResponse(
        access_token=token,
        expires_in=req.ttl_hours * 3600,
        role=expected_role,
        workspace_id=req.workspace_id,
    )


class IntrospectRequest(BaseModel):
    token: str


@router.post("/introspect")
async def introspect(req: IntrospectRequest) -> dict:
    """Return the claims of a JWT if it is valid. 401 otherwise.

    Useful for debugging and for downstream services that want to verify
    a token without re-implementing the decode step.
    """
    try:
        claims = decode_access_token(req.token)
    except JWTError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    return {"active": True, "claims": claims}
