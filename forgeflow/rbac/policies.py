"""RBAC policy definitions — role → allowed permissions, route → required permission.

Hardening (SECURITY_AUDIT.md API5):
  - Every route exposed by the API is mapped here. Unmapped requests are
    denied by RBACMiddleware (fail closed).
  - Longest-prefix match in the middleware so /workflows/{id}/trace doesn't
    inherit /workflows's broad "read:workflows" grant.
  - 'service' role is for service-to-service JWTs (sub starts with "service:");
    it intentionally does NOT carry *:* — pick the precise permissions.
"""

from __future__ import annotations

# Role → set of "action:resource" permission strings. "*:*" = unrestricted.
ROLE_PERMISSIONS: dict[str, set[str]] = {
    "admin": {"*:*"},
    "manager": {
        "read:workflows",
        "read:metrics",
        "read:leads",
        "read:proposals",
        "approve:proposals",
        "read:agents",
        "send:agents",
        "read:memory",
        "read:audit",
        "read:workspaces",
        "read:marketplace",
    },
    "sales_rep": {
        "execute:workflows",
        "read:workflows",
        "read:metrics",
        "read:memory",
        "write:memory",
        "read:agents",
        "read:marketplace",
    },
    "viewer": {
        "read:metrics",
        "read:workflows",
        "read:marketplace",
    },
    "anonymous": {
        # Marketplace listing is intentionally public — discovery is the point.
        "read:marketplace",
    },
    # Narrow service identity — pick exactly what the cron / dispatcher needs.
    "service": {
        "read:metrics",
        "read:workflows",
        "execute:workflows",
    },
}

# Maps HTTP (method, path prefix) → (action, resource).
# Longest-prefix match wins. Every route MUST appear here — RBACMiddleware
# denies unmapped routes (fail-closed). When you add a new router, add its
# entries here in the same commit.
ROUTE_PERMISSION_MAP: dict[tuple[str, str], tuple[str, str]] = {
    # --- workflows ---
    ("POST",   "/workflows/run"):                 ("execute", "workflows"),
    ("POST",   "/workflows/stream"):              ("execute", "workflows"),
    ("GET",    "/workflows"):                     ("read",    "workflows"),
    # Trace exposes prompts + LLM output → require explicit perm
    ("GET",    "/workflows/trace"):               ("read",    "workflows"),  # legacy
    # --- approvals ---
    ("POST",   "/approvals"):                     ("approve", "proposals"),
    ("GET",    "/approvals"):                     ("read",    "proposals"),
    # --- agents ---
    ("GET",    "/agents"):                        ("read",    "agents"),
    ("POST",   "/agents"):                        ("send",    "agents"),
    # --- memory ---
    ("GET",    "/memory"):                        ("read",    "memory"),
    ("POST",   "/memory"):                        ("write",   "memory"),
    ("DELETE", "/memory"):                        ("write",   "memory"),
    # --- metrics ---
    ("GET",    "/metrics"):                       ("read",    "metrics"),
    # --- audit ---
    ("GET",    "/audit"):                         ("read",    "audit"),
    # --- workspaces ---
    ("GET",    "/workspaces"):                    ("read",    "workspaces"),
    ("POST",   "/workspaces"):                    ("write",   "workspaces"),
    # --- marketplace ---
    ("GET",    "/marketplace"):                   ("read",    "marketplace"),
    ("POST",   "/marketplace/templates/refresh"): ("write",   "marketplace"),
}
