"""Tests for RBAC policy enforcement."""

from __future__ import annotations

import pytest

from forgeflow.rbac.enforcer import RBACEnforcer


class TestRBACEnforcer:
    def setup_method(self):
        self.enforcer = RBACEnforcer()

    def test_admin_can_do_anything(self):
        assert self.enforcer.check("admin", "execute", "workflows")
        assert self.enforcer.check("admin", "approve", "proposals")
        assert self.enforcer.check("admin", "delete", "anything")

    def test_sales_rep_can_execute_workflows(self):
        assert self.enforcer.check("sales_rep", "execute", "workflows")

    def test_sales_rep_cannot_approve_proposals(self):
        assert not self.enforcer.check("sales_rep", "approve", "proposals")

    def test_manager_can_approve(self):
        assert self.enforcer.check("manager", "approve", "proposals")

    def test_manager_cannot_execute_workflows(self):
        assert not self.enforcer.check("manager", "execute", "workflows")

    def test_viewer_can_read_metrics(self):
        assert self.enforcer.check("viewer", "read", "metrics")

    def test_viewer_cannot_execute(self):
        assert not self.enforcer.check("viewer", "execute", "workflows")

    def test_unknown_role_denied(self):
        assert not self.enforcer.check("hacker", "execute", "workflows")

    def test_anonymous_denied(self):
        assert not self.enforcer.check("anonymous", "read", "metrics")
