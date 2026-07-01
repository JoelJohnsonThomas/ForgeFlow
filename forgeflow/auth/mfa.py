"""TOTP multi-factor auth (RFC 6238) via pyotp.

Enrollment generates a base32 secret and an otpauth:// URI that authenticator
apps (Google Authenticator, 1Password, Authy) render as a QR code. Verification
allows a ±1 step window to tolerate clock skew.
"""

from __future__ import annotations

import pyotp

_ISSUER = "ForgeFlow"


def generate_secret() -> str:
    """Return a fresh base32 TOTP secret to store against the user."""
    return pyotp.random_base32()


def provisioning_uri(username: str, secret: str) -> str:
    """otpauth:// URI for QR enrollment in an authenticator app."""
    return pyotp.TOTP(secret).provisioning_uri(name=username, issuer_name=_ISSUER)


def verify_code(secret: str | None, code: str | None, *, window: int = 1) -> bool:
    """Verify a 6-digit TOTP code. Returns False (never raises) on any bad input.
    `window=1` accepts the previous/next 30s step to tolerate clock drift."""
    if not secret or not code:
        return False
    try:
        return pyotp.TOTP(secret).verify(str(code).strip(), valid_window=window)
    except Exception:  # noqa: BLE001
        return False
