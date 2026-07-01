"""Auth routes — enterprise credential flow (Increment 2).

Replaces the shared-password demo with:
  * Argon2id password verification against the `users` table.
  * TOTP MFA (enroll + verify + enforced at login).
  * Short-lived access JWTs + rotating, reuse-detecting refresh tokens.
  * OIDC exchange — verify an external IdP id_token and mint local tokens.

Posture: password login (/auth/login) is the local/dev path and is gated by
DEV_LOGIN_ENABLED. Production fronts the API with an IdP and uses
/auth/oidc/exchange. Both issue the same access+refresh token pair.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from forgeflow.api.dependencies import get_current_user, get_pool
from forgeflow.auth import mfa, passwords, tokens
from forgeflow.auth import users as user_store
from forgeflow.auth.jwt import (
    JWTError,
    create_access_token,
    decode_access_token,
    revoke_token,
)
from forgeflow.auth.membership import user_is_member
from forgeflow.auth.oidc import OIDCError, verify_oidc_token
from forgeflow.config import get_settings
from forgeflow.rbac.models import UserContext

logger = logging.getLogger(__name__)
router = APIRouter()

_LOGIN_WINDOW_S = 60.0
_LOGIN_MAX_ATTEMPTS = 5
_attempts: dict[str, list[float]] = defaultdict(list)


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #
class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(..., min_length=1, max_length=128)
    password: str = Field(..., min_length=1, max_length=256)
    workspace_id: str | None = None
    ttl_hours: int = Field(1, ge=1, le=24)
    mfa_code: str | None = Field(None, max_length=12)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    role: str
    workspace_id: str | None = None


class RefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    refresh_token: str = Field(..., min_length=1)


class LogoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str | None = None
    refresh_token: str | None = None


class OIDCExchangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id_token: str = Field(..., min_length=1)


class MfaVerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(..., min_length=6, max_length=12)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _client_ip(request: Request) -> str:
    settings = get_settings()
    if settings.trusted_proxy_count > 0:
        xff = request.headers.get("x-forwarded-for", "")
        parts = [p.strip() for p in xff.split(",") if p.strip()]
        idx = -settings.trusted_proxy_count
        if -idx <= len(parts):
            return parts[idx]
    return request.client.host if request.client else "unknown"


def _rate_limit_login(ip: str) -> None:
    now = time.monotonic()
    bucket = [t for t in _attempts[ip] if now - t < _LOGIN_WINDOW_S]
    _attempts[ip] = bucket
    if len(bucket) >= _LOGIN_MAX_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Too many login attempts. Try again in a minute.")
    bucket.append(now)


async def _issue_tokens(
    pool: asyncpg.Pool, user: asyncpg.Record, workspace_id: str | None, ttl_hours: int
) -> TokenResponse:
    """Mint an access JWT (sub=username for backward compat) + a refresh token."""
    access = create_access_token(
        user_id=user["username"],
        role=user["role"],
        workspace_id=workspace_id,
        ttl_hours=ttl_hours,
    )
    refresh = await tokens.issue_refresh_token(pool, user["id"])
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=ttl_hours * 3600,
        role=user["role"],
        workspace_id=workspace_id,
    )


# --------------------------------------------------------------------------- #
# Password login (local / dev path)
# --------------------------------------------------------------------------- #
@router.post("/login", response_model=TokenResponse)
async def login(
    req: LoginRequest,
    request: Request,
    pool: asyncpg.Pool = Depends(get_pool),
) -> TokenResponse:
    """Password + optional MFA login against the users table. 404 when
    DEV_LOGIN_ENABLED=false (production uses /auth/oidc/exchange)."""
    settings = get_settings()
    if not settings.dev_login_enabled:
        raise HTTPException(status_code=404, detail="not found")

    ip = _client_ip(request)
    _rate_limit_login(ip)

    user = await user_store.get_by_username(pool, req.user_id)
    # Verify password even when the user is missing to keep timing uniform.
    stored_hash = user["password_hash"] if user else None
    if not passwords.verify_password(stored_hash, req.password) or user is None or user["disabled"]:
        raise HTTPException(status_code=401, detail="invalid credentials")

    # MFA enforcement.
    if user["mfa_enabled"]:
        if not req.mfa_code:
            raise HTTPException(status_code=401, detail="mfa_required")
        if not mfa.verify_code(user["mfa_secret"], req.mfa_code):
            raise HTTPException(status_code=401, detail="invalid mfa code")

    # Optional workspace claim — verified against membership (C-4 fix).
    workspace_id: str | None = None
    if req.workspace_id:
        if not await user_is_member(pool, str(user["id"]), req.workspace_id):
            logger.warning("Workspace claim rejected | user=%s ws=%s", req.user_id, req.workspace_id)
            raise HTTPException(status_code=403, detail="not a member of the requested workspace")
        workspace_id = req.workspace_id

    return await _issue_tokens(pool, user, workspace_id, req.ttl_hours)


# --------------------------------------------------------------------------- #
# Refresh (rotation + reuse detection)
# --------------------------------------------------------------------------- #
@router.post("/refresh", response_model=TokenResponse)
async def refresh(req: RefreshRequest, pool: asyncpg.Pool = Depends(get_pool)) -> TokenResponse:
    """Exchange a refresh token for a new access+refresh pair. Reusing a rotated
    token revokes the whole family."""
    try:
        result = await tokens.rotate(pool, req.refresh_token)
    except tokens.RefreshError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    user = result["user"]
    access = create_access_token(
        user_id=user["username"],
        role=user["role"],
        ttl_hours=get_settings().access_token_ttl_hours,
    )
    return TokenResponse(
        access_token=access,
        refresh_token=result["refresh_token"],
        expires_in=get_settings().access_token_ttl_hours * 3600,
        role=user["role"],
    )


# --------------------------------------------------------------------------- #
# Logout
# --------------------------------------------------------------------------- #
@router.post("/logout")
async def logout(req: LogoutRequest, pool: asyncpg.Pool = Depends(get_pool)) -> dict:
    """Revoke the access token (jti denylist) and/or the refresh-token family."""
    if req.token:
        try:
            claims = decode_access_token(req.token)
            jti, exp = claims.get("jti"), int(claims.get("exp", 0))
            if jti and exp:
                revoke_token(str(jti), exp)
        except JWTError as exc:
            logger.info("logout for invalid access token: %s", exc)
    if req.refresh_token:
        await tokens.revoke_by_token(pool, req.refresh_token)
    return {"revoked": True}


# --------------------------------------------------------------------------- #
# MFA enrollment (authenticated)
# --------------------------------------------------------------------------- #
@router.post("/mfa/enroll")
async def mfa_enroll(
    pool: asyncpg.Pool = Depends(get_pool),
    ctx: UserContext = Depends(get_current_user),
) -> dict:
    """Stage a TOTP secret for the current user and return its otpauth URI.
    MFA is not enforced until /auth/mfa/verify succeeds."""
    user = await user_store.get_by_username(pool, ctx.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    secret = mfa.generate_secret()
    await user_store.set_mfa_secret(pool, user["id"], secret)
    return {
        "secret": secret,
        "otpauth_uri": mfa.provisioning_uri(user["username"], secret),
        "note": "Scan in an authenticator app, then POST /auth/mfa/verify with a code to enable.",
    }


@router.post("/mfa/verify")
async def mfa_verify(
    body: MfaVerifyRequest,
    pool: asyncpg.Pool = Depends(get_pool),
    ctx: UserContext = Depends(get_current_user),
) -> dict:
    """Confirm the staged TOTP secret with a live code and enable MFA."""
    user = await user_store.get_by_username(pool, ctx.user_id)
    if user is None or not user["mfa_secret"]:
        raise HTTPException(status_code=400, detail="no MFA enrollment in progress")
    if not mfa.verify_code(user["mfa_secret"], body.code):
        raise HTTPException(status_code=401, detail="invalid mfa code")
    await user_store.enable_mfa(pool, user["id"])
    return {"mfa_enabled": True}


# --------------------------------------------------------------------------- #
# OIDC exchange (production SSO)
# --------------------------------------------------------------------------- #
@router.post("/oidc/exchange", response_model=TokenResponse)
async def oidc_exchange(
    body: OIDCExchangeRequest, pool: asyncpg.Pool = Depends(get_pool)
) -> TokenResponse:
    """Verify an external IdP id_token and mint local tokens for the mapped user."""
    settings = get_settings()
    if not settings.oidc_enabled:
        raise HTTPException(status_code=404, detail="OIDC not enabled")
    try:
        claims = verify_oidc_token(body.id_token)
    except OIDCError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    subject = str(claims["sub"])
    username = str(claims.get("preferred_username") or claims.get("email") or subject)
    user = await user_store.provision_oidc_user(
        pool, subject, username, settings.oidc_default_role
    )
    return await _issue_tokens(pool, user, workspace_id=None, ttl_hours=settings.access_token_ttl_hours)


# --------------------------------------------------------------------------- #
# Introspection
# --------------------------------------------------------------------------- #
class IntrospectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str


@router.post("/introspect")
async def introspect(req: IntrospectRequest) -> dict:
    """Return the claims of a valid access JWT; 401 otherwise."""
    try:
        claims = decode_access_token(req.token)
    except JWTError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return {"active": True, "claims": claims}


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, TypeError):
        return False
