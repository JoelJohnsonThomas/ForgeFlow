"""006 - Fix approval_requests.resolved_by type.

The column was declared UUID, but every code path (and the dev-login users)
store a string user id like "manager-1" / "controller". Approving or rejecting
therefore 500s with `invalid UUID '<user_id>'`. Widen the column to VARCHAR so
it matches the application's user-id model.

Revision ID: 006
Revises: 005
Create Date: 2026-06-30
"""

from alembic import op

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE approval_requests
            ALTER COLUMN resolved_by TYPE VARCHAR(128) USING resolved_by::text
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE approval_requests
            ALTER COLUMN resolved_by TYPE UUID USING resolved_by::uuid
        """
    )
