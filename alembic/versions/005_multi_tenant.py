"""005 - Multi-tenant foundation: workspaces table + workspace_id columns.

This is the schema foundation for Phase 3.5 multi-tenant isolation. It adds
the workspaces table and nullable workspace_id columns to the user-data
tables. It does NOT add NOT NULL constraints or rewrite existing queries —
that's a separate migration once all callers send workspace_id.

Tables touched (workspace_id added, NULLable, default NULL):
  - workflow_runs
  - approval_requests
  - leads
  - proposals
  - audit_log (partitioned -> ALTER must run per partition)
  - run_metrics
  - memory_vectors

Tables NOT touched here:
  - agent_traces (foreign-keyed to workflow_runs, inherits scoping)
  - roles / permissions / role_permissions (global, not tenant-scoped)

Revision ID: 005
Revises: 004
Create Date: 2026-05-20
"""

from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Workspaces — the tenant root entity. UUID PK so external systems can
    # mint them; slug for human-friendly URLs; settings for per-tenant
    # overrides (budget caps, allowed providers, custom branding).
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS workspaces (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            slug        VARCHAR(64) UNIQUE NOT NULL,
            name        VARCHAR(256) NOT NULL,
            settings    JSONB NOT NULL DEFAULT '{}',
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            archived_at TIMESTAMPTZ
        )
        """
    )

    # Seed a 'default' workspace so existing single-tenant deployments
    # have something to migrate their NULL workspace_ids into when ready.
    op.execute(
        """
        INSERT INTO workspaces (slug, name)
        VALUES ('default', 'Default Workspace')
        ON CONFLICT (slug) DO NOTHING
        """
    )

    # Add workspace_id columns (NULLable, no FK yet — keeps the migration
    # cheap on big tables and lets us backfill out-of-band).
    for table in (
        "workflow_runs",
        "approval_requests",
        "leads",
        "proposals",
        "run_metrics",
        "memory_vectors",
    ):
        op.execute(
            f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS workspace_id UUID"
        )
        op.execute(
            f"CREATE INDEX IF NOT EXISTS idx_{table}_workspace_id "
            f"ON {table}(workspace_id) WHERE workspace_id IS NOT NULL"
        )

    # audit_log is partitioned — ALTER cascades to each partition automatically
    op.execute("ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS workspace_id UUID")

    # Add workspace membership table — links users to workspaces with a role.
    # Roles here override the per-user role for that workspace's resources.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS workspace_members (
            workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            user_id      UUID NOT NULL,
            role         VARCHAR(64) NOT NULL,
            joined_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (workspace_id, user_id)
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_workspace_members_user "
        "ON workspace_members(user_id)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS workspace_members")

    for table in (
        "workflow_runs",
        "approval_requests",
        "leads",
        "proposals",
        "run_metrics",
        "memory_vectors",
        "audit_log",
    ):
        op.execute(f"DROP INDEX IF EXISTS idx_{table}_workspace_id")
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS workspace_id")

    op.execute("DROP TABLE IF EXISTS workspaces")
