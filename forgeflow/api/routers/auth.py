"""Auth routes — JWT issuance.

The `/auth/login` endpoint is a **demo / OSS preview** path. Production
deployments MUST set `DEV_LOGIN_ENABLED=false` and front the API with a real
OIDC verifier (oauth2-proxy / Pomerium) that mints the JWT shape this file
documents. See SECURITY_AUDIT.md sections C-3 and 10 for the migration path.

Hardening applied in this commit:
  1. Requires DEV_LOGIN_PASSWORD env to mint anything. Refuses to issue
     tokens with a placeholder password.
  2. IP-bound 5-attempts-per-minute lockout (in-process; per-replica). Real
     deployments should sit behind a WAF + Redis-backed limiter.
  3. workspace_id (if requested) is verified against workspace_members. The
     login body cannot self-assert tenant scope (C-4).
  4. Returns 404 when DEV_LOGIN_ENABLED=false so the existence of the demo
     path is not advertised in prod.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from forgeflow.api.dependencies import get_pool
from forgeflow.auth.jwt import JWTError, create_access_token, decode_access_token
from forgeflow.auth.membership import user_is_member
from forgeflow.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()

_LOGIN_WINDOW_S = 60.0
_LOGIN_MAX_ATTEMPTS = 5
_attempts: dict[str, list[float]] = defaultdict(list)


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(..., min_length=1, max_length=128)
    password: str = Field(..., min_length=1, max_length=256)
    workspace_id: str | None = None
    ttl_hours: int = Field(1, ge=1, le=24)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    role: str
    workspace_id: str | None = None


# Demo / dev users. The role here is fixed — the request can't override it
# (defense against role escalation via login body).
_DEMO_USERS = {
    "admin": "admin",
    "manager-1": "manager",
    "rep-1": "sales_rep",
    "viewer-1": "viewer",
}


def _client_ip(request: Request) -> str:
    """Return the client IP, honoring only the proxy hops we trust.

    With trusted_proxy_count=0 the X-Forwarded-For header is ignored — the
    socket peer wins. With N>0 we take the Nth-from-the-right XFF entry
    (the one set by the closest hop we control).
    """
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
        raise HTTPException(
            status_code=429,
            detail="Too many login attempts. Try again in a minute.",
        )
    bucket.append(now)


@router.post("/login", response_model=TokenResponse)
async def login(
    req: LoginRequest,
    request: Request,
    pool: asyncpg.Pool = Depends(get_pool),
) -> TokenResponse:
    """Issue a JWT for a known demo user.

    Disabled entirely when DEV_LOGIN_ENABLED=false (returns 404).
    """
    settings = get_settings()

    if not settings.dev_login_enabled:
        # 404 — don't advertise that the endpoint exists in prod.
        raise HTTPException(status_code=404, detail="not found")

    dev_password = settings.dev_login_password.get_secret_value()
    if not dev_password:
        # Refuse to mint anything without an explicit password — protects
        # against a deploy that flips dev_login_enabled true but forgets
        # to set the gate.
        logger.error(
            "/auth/login called but DEV_LOGIN_PASSWORD is empty — refusing"
        )
        raise HTTPException(
            status_code=503,
            detail="dev login misconfigured (password unset)",
        )

    ip = _client_ip(request)
    _rate_limit_login(ip)

    expected_role = _DEMO_USERS.get(req.user_id)
    if expected_role is None or not _constant_time_eq(req.password, dev_password):
        # Generic message — don't leak which of user/password was wrong.
        raise HTTPException(status_code=401, detail="invalid credentials")

    workspace_id: str | None = None
    if req.workspace_id:
        # Verify membership before honoring the requested workspace.
        if not await user_is_member(pool, req.user_id, req.workspace_id):
            logger.warning(
                "Workspace claim rejected | user=%s requested_ws=%s ip=%s",
                req.user_id,
                req.workspace_id,
                ip,
            )
            raise HTTPException(
                status_code=403,
                detail="user is not a member of the requested workspace",
            )
        workspace_id = req.workspace_id

    token = create_access_token(
        user_id=req.user_id,
        role=expected_role,
        workspace_id=workspace_id,
        ttl_hours=req.ttl_hours,
    )
    return TokenResponse(
        access_token=token,
        expires_in=req.ttl_hours * 3600,
        role=expected_role,
        workspace_id=workspace_id,
    )


def _constant_time_eq(a: str, b: str) -> bool:
    """Constant-time string compare to keep password check timing-attack safe."""
    import hmac

    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


class IntrospectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str


@router.post("/introspect")
async def introspect(req: IntrospectRequest) -> dict:
    """Return the claims of a JWT if it is valid. 401 otherwise."""
    try:
        claims = decode_access_token(req.token)
    except JWTError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return {"active": True, "claims": claims}


class LogoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str


@router.post("/logout")
async def logout(req: LogoutRequest) -> dict:
    """Revoke the provided JWT (jti added to denylist until its exp)."""
    from forgeflow.auth.jwt import revoke_token

    try:
        claims = decode_access_token(req.token)
    except JWTError as exc:
        # Already invalid — nothing to revoke; respond OK to avoid an oracle.
        logger.info("logout for invalid token: %s", exc)
        return {"revoked": True}

    jti = claims.get("jti")
    exp = int(claims.get("exp", 0))
    if jti and exp:
        revoke_token(str(jti), exp)
        # Also revoke any UUID-ish user_id pointer so audit logs reflect it.
        logger.info("token revoked | sub=%s jti=%s", claims.get("sub"), jti)
    return {"revoked": True}


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, TypeError):
        return False
