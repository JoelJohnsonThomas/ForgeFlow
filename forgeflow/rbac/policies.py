"""RBAC policy definitions — role → allowed permissions."""

from __future__ import annotations

# Role → set of "action:resource" permission strings
# "*:*" means full access (admin only)
ROLE_PERMISSIONS: dict[str, set[str]] = {
    "admin": {"*:*"},
    "manager": {
        "read:workflows",
        "read:metrics",
        "read:leads",
        "read:proposals",
        "approve:proposals",
        "read:agents",
        "read:memory",
        "read:audit",
    },
    "sales_rep": {
        "execute:workflows",
        "read:workflows",
        "read:metrics",
        "read:memory",
        "write:memory",
        "read:agents",
    },
    "viewer": {
        "read:metrics",
        "read:workflows",
    },
    "anonymous": set(),
}

# Maps HTTP (method, path prefix) → (action, resource)
# Used by the RBAC middleware to determine required permission
ROUTE_PERMISSION_MAP: dict[tuple[str, str], tuple[str, str]] = {
    ("POST", "/workflows/run"):          ("execute", "workflows"),
    ("POST", "/workflows/stream"):       ("execute", "workflows"),
    ("GET",  "/workflows"):              ("read",    "workflows"),
    ("POST", "/approvals"):              ("approve", "proposals"),
    ("GET",  "/approvals"):              ("read",    "proposals"),
    ("GET",  "/agents"):                 ("read",    "agents"),
    ("GET",  "/metrics"):                ("read",    "metrics"),
    ("GET",  "/memory"):                 ("read",    "memory"),
    ("POST", "/memory"):                 ("write",   "memory"),
    ("DELETE", "/memory"):               ("write",   "memory"),
    ("GET",  "/audit"):                  ("read",    "audit"),
}
