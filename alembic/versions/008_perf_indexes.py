"""008 - Performance indexes for run listing + ownership filters.

After 007 the read endpoints filter workflow_runs by user_id (object-level
authorization) and the console lists runs by (workspace_id, status, recency).
Neither path was indexed, so both were sequential scans that degrade as the
table grows. These indexes make them index scans.

Revision ID: 008
Revises: 007
Create Date: 2026-06-30
"""

from alembic import op

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ownership filter on the run read/trace endpoints.
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_workflow_runs_user_id "
        "ON workflow_runs (user_id)"
    )
    # Console run listing: newest-first within a tenant, optionally by status.
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_workflow_runs_ws_status_created "
        "ON workflow_runs (workspace_id, status, created_at DESC)"
    )
    # Approval lookups by run.
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_approval_requests_run "
        "ON approval_requests (run_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_approval_requests_run")
    op.execute("DROP INDEX IF EXISTS idx_workflow_runs_ws_status_created")
    op.execute("DROP INDEX IF EXISTS idx_workflow_runs_user_id")
