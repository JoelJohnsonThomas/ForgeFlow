"""004 - Approval escalation fields.

Adds escalation tracking to approval_requests so the background escalation
task can ratchet stale approvals through warning -> escalated -> auto-rejected.

Revision ID: 004
Revises: 003
Create Date: 2026-05-20
"""

from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE approval_requests
            ADD COLUMN IF NOT EXISTS escalation_level   INT NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS last_escalated_at  TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS escalated_to       VARCHAR(64),
            ADD COLUMN IF NOT EXISTS auto_resolved      BOOLEAN NOT NULL DEFAULT FALSE
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_approval_requests_pending_age
            ON approval_requests (status, requested_at)
            WHERE status = 'pending'
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_approval_requests_pending_age")
    op.execute(
        """
        ALTER TABLE approval_requests
            DROP COLUMN IF EXISTS auto_resolved,
            DROP COLUMN IF EXISTS escalated_to,
            DROP COLUMN IF EXISTS last_escalated_at,
            DROP COLUMN IF EXISTS escalation_level
        """
    )
