"""Password hashing — Argon2id (OWASP-recommended KDF).

Argon2id is memory-hard and resistant to GPU/ASIC cracking. We keep a module
-level PasswordHasher with sane defaults; `needs_rehash` lets us transparently
upgrade parameters on the next successful login.
"""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

# Defaults follow argon2-cffi's recommended profile; tune per infra if needed.
_hasher = PasswordHasher()


def hash_password(plaintext: str) -> str:
    """Return an Argon2id encoded hash (includes salt + params)."""
    return _hasher.hash(plaintext)


def verify_password(encoded_hash: str | None, plaintext: str) -> bool:
    """Constant-time verify. Returns False (never raises) on any mismatch or
    malformed/absent hash, so callers can branch without leaking which failed."""
    if not encoded_hash:
        return False
    try:
        return _hasher.verify(encoded_hash, plaintext)
    except (VerifyMismatchError, InvalidHashError, Exception):  # noqa: BLE001
        return False


def needs_rehash(encoded_hash: str) -> bool:
    """True when the stored hash used weaker params than the current policy."""
    try:
        return _hasher.check_needs_rehash(encoded_hash)
    except Exception:  # noqa: BLE001
        return False
