"""RBACEnforcer — checks if a role has permission to perform an action."""

from __future__ import annotations

from forgeflow.rbac.policies import ROLE_PERMISSIONS


class RBACEnforcer:
    def check(self, role: str, action: str, resource: str) -> bool:
        """Return True if the role is allowed to perform action on resource."""
        permissions = ROLE_PERMISSIONS.get(role, set())

        if "*:*" in permissions:
            return True

        if f"{action}:{resource}" in permissions:
            return True

        # Wildcard resource: "action:*"
        if f"{action}:*" in permissions:
            return True

        return False
