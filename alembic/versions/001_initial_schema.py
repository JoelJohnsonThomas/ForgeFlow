"""001 — Initial schema: workflow_runs, agent_traces, approval_requests, leads, proposals.

Revision ID: 001
Revises: (none)
Create Date: 2026-05-19
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # workflow_runs — one row per workflow execution                       #
    # ------------------------------------------------------------------ #
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    op.create_table(
        "workflow_runs",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("thread_id", UUID, nullable=False),
        sa.Column("workflow_type", sa.String(64), nullable=False, server_default="sales_ops"),
        sa.Column("status", sa.String(32), nullable=False, server_default="running"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("input_data", JSONB, nullable=False, server_default="{}"),
        sa.Column("output_data", JSONB, nullable=True),
        sa.Column("total_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_cost_usd", sa.Numeric(10, 6), nullable=False, server_default="0"),
        sa.Column("user_id", UUID, nullable=True),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
    )
    op.create_index("idx_workflow_runs_thread", "workflow_runs", ["thread_id"])
    op.create_index("idx_workflow_runs_status", "workflow_runs", ["status"])
    op.create_index(
        "idx_workflow_runs_created",
        "workflow_runs",
        [sa.text("created_at DESC")],
    )

    # ------------------------------------------------------------------ #
    # agent_traces — one row per node invocation within a run             #
    # ------------------------------------------------------------------ #
    op.create_table(
        "agent_traces",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("run_id", UUID, sa.ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_name", sa.String(64), nullable=False),
        sa.Column("stage", sa.String(64), nullable=False),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("input_state", JSONB, nullable=True),
        sa.Column("output_patch", JSONB, nullable=True),
        sa.Column("tokens_used", sa.Integer, nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Numeric(10, 6), nullable=False, server_default="0"),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("langsmith_run_id", sa.String(128), nullable=True),
    )
    op.create_index("idx_agent_traces_run", "agent_traces", ["run_id"])

    # ------------------------------------------------------------------ #
    # approval_requests — human-in-the-loop queue                         #
    # ------------------------------------------------------------------ #
    op.create_table(
        "approval_requests",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("run_id", UUID, sa.ForeignKey("workflow_runs.id"), nullable=False),
        sa.Column("token", UUID, nullable=False, unique=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("stage", sa.String(64), nullable=False),
        sa.Column("payload", JSONB, nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("requested_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("resolved_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("resolved_by", UUID, nullable=True),
        sa.Column("resolution_note", sa.Text, nullable=True),
        sa.Column(
            "expires_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now() + INTERVAL '24 hours'"),
        ),
    )
    op.create_index("idx_approval_requests_token", "approval_requests", ["token"])
    op.create_index("idx_approval_requests_status", "approval_requests", ["status"])

    # ------------------------------------------------------------------ #
    # leads — sales domain entity                                         #
    # ------------------------------------------------------------------ #
    op.create_table(
        "leads",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("run_id", UUID, sa.ForeignKey("workflow_runs.id"), nullable=True),
        sa.Column("company_name", sa.String(256), nullable=False),
        sa.Column("contact_name", sa.String(256), nullable=True),
        sa.Column("contact_email", sa.String(256), nullable=True),
        sa.Column("industry", sa.String(128), nullable=True),
        sa.Column("employee_count", sa.Integer, nullable=True),
        sa.Column("annual_revenue", sa.BigInteger, nullable=True),
        sa.Column("qualification_score", sa.Numeric(4, 2), nullable=True),
        sa.Column("status", sa.String(64), nullable=False, server_default="raw"),
        sa.Column("raw_data", JSONB, nullable=False, server_default="{}"),
        sa.Column("enriched_data", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_leads_status", "leads", ["status"])

    # ------------------------------------------------------------------ #
    # proposals — AI-generated sales proposals                            #
    # ------------------------------------------------------------------ #
    op.create_table(
        "proposals",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("lead_id", UUID, sa.ForeignKey("leads.id"), nullable=False),
        sa.Column("run_id", UUID, sa.ForeignKey("workflow_runs.id"), nullable=True),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("pricing", JSONB, nullable=True),
        sa.Column("risk_flags", JSONB, nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
    )


def downgrade() -> None:
    op.drop_table("proposals")
    op.drop_table("leads")
    op.drop_table("approval_requests")
    op.drop_table("agent_traces")
    op.drop_table("workflow_runs")
