"""Per-workspace outbound email allowlist.

SECURITY_AUDIT.md C-5 / §7 — email_send is one of the highest-impact
side-effect tools; any LLM-controlled recipient is an exfiltration channel.
Two layers of defense:

  1. Hard recipient pin (caller's responsibility): the Executor agent only
     sends to `lead_data.contact_email`, never to an address from the LLM
     output.
  2. Per-workspace domain allowlist (this module): every recipient is
     checked against the workspace's `settings.email_allowed_domains` list.
     Empty list = wildcard (dev fallback). The MCP tool consults this
     before any send.

Allowed-domain list is stored in workspaces.settings JSONB so tenants can
configure it through the admin API:

  UPDATE workspaces
  SET settings = jsonb_set(settings, '{email_allowed_domains}',
                           '["example.com", "*.partner.com"]')
  WHERE slug = 'acme';
"""

from __future__ import annotations

import fnmatch
import logging
from collections.abc import Iterable

logger = logging.getLogger(__name__)


class EmailNotAllowed(ValueError):
    """Raised when an outbound recipient violates the workspace allowlist."""


def _normalise(domain: str) -> str:
    return domain.strip().lower().lstrip("@")


def is_recipient_allowed(recipient: str, allowed_domains: Iterable[str]) -> bool:
    """Match recipient's domain against the allowlist (fnmatch patterns OK)."""
    if "@" not in recipient:
        return False
    domain = recipient.rsplit("@", 1)[1].lower()

    patterns = [_normalise(d) for d in allowed_domains if d]
    if not patterns:
        # Empty list = wildcard. Documented as dev fallback in the docstring.
        return True

    return any(fnmatch.fnmatch(domain, pattern) for pattern in patterns)


def require_allowed(recipient: str, allowed_domains: Iterable[str]) -> None:
    if not is_recipient_allowed(recipient, allowed_domains):
        raise EmailNotAllowed(
            f"recipient '{recipient}' is not in the workspace email allowlist"
        )
