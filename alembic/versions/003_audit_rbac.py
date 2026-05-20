"""003 — Audit log (partitioned by month) + RBAC tables + run_metrics.

Revision ID: 003
Revises: 002
Create Date: 2026-05-19
"""


from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # audit_log — immutable, partitioned by month                         #
    # ------------------------------------------------------------------ #
    op.execute("""
        CREATE TABLE audit_log (
            id          BIGSERIAL,
            timestamp   TIMESTAMPTZ NOT NULL DEFAULT now(),
            user_id     UUID,
            role        VARCHAR(64),
            action      VARCHAR(128) NOT NULL,
            resource    VARCHAR(128) NOT NULL,
            resource_id VARCHAR(128),
            outcome     VARCHAR(32) NOT NULL,
            request_id  UUID,
            ip_address  INET,
            metadata    JSONB NOT NULL DEFAULT '{}'
        ) PARTITION BY RANGE (timestamp)
    """)

    # Create initial partitions (2025–2026)
    op.execute("""
        CREATE TABLE audit_log_2025 PARTITION OF audit_log
        FOR VALUES FROM ('2025-01-01') TO ('2026-01-01')
    """)
    op.execute("""
        CREATE TABLE audit_log_2026 PARTITION OF audit_log
        FOR VALUES FROM ('2026-01-01') TO ('2027-01-01')
    """)
    op.execute("CREATE INDEX idx_audit_log_timestamp ON audit_log(timestamp DESC)")
    op.execute("CREATE INDEX idx_audit_log_user ON audit_log(user_id)")
    op.execute("CREATE INDEX idx_audit_log_resource ON audit_log(resource, resource_id)")

    # ------------------------------------------------------------------ #
    # RBAC — roles, permissions, users                                    #
    # ------------------------------------------------------------------ #
    op.execute("""
        CREATE TABLE roles (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name        VARCHAR(64) UNIQUE NOT NULL,
            description TEXT,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("""
        CREATE TABLE permissions (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            action      VARCHAR(64) NOT NULL,
            resource    VARCHAR(64) NOT NULL,
            UNIQUE (action, resource)
        )
    """)
    op.execute("""
        CREATE TABLE role_permissions (
            role_id       UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
            permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
            PRIMARY KEY (role_id, permission_id)
        )
    """)
    op.execute("""
        CREATE TABLE users (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email           VARCHAR(256) UNIQUE NOT NULL,
            name            VARCHAR(256),
            role_id         UUID REFERENCES roles(id),
            api_key_hash    VARCHAR(128),
            active          BOOLEAN NOT NULL DEFAULT true,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # Seed default roles
    op.execute("""
        INSERT INTO roles (name, description) VALUES
        ('admin',     'Full system access'),
        ('manager',   'Can approve proposals and view all metrics'),
        ('sales_rep', 'Can run workflows and view own metrics'),
        ('viewer',    'Read-only access to metrics')
    """)

    op.execute("""
        INSERT INTO permissions (action, resource) VALUES
        ('execute', 'workflows'),
        ('read',    'workflows'),
        ('approve', 'proposals'),
        ('read',    'proposals'),
        ('read',    'leads'),
        ('write',   'leads'),
        ('read',    'metrics'),
        ('read',    'memory'),
        ('write',   'memory'),
        ('read',    'agents'),
        ('admin',   '*')
    """)

    # ------------------------------------------------------------------ #
    # run_metrics — time-series metrics for dashboard                     #
    # ------------------------------------------------------------------ #
    op.execute("""
        CREATE TABLE run_metrics (
            id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            run_id       UUID NOT NULL REFERENCES workflow_runs(id) ON DELETE CASCADE,
            metric_name  VARCHAR(128) NOT NULL,
            metric_value NUMERIC(18,6) NOT NULL,
            metric_unit  VARCHAR(32),
            recorded_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            tags         JSONB NOT NULL DEFAULT '{}'
        )
    """)
    op.execute("CREATE INDEX idx_run_metrics_name_time ON run_metrics(metric_name, recorded_at DESC)")
    op.execute("CREATE INDEX idx_run_metrics_run ON run_metrics(run_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS run_metrics")
    op.execute("DROP TABLE IF EXISTS users")
    op.execute("DROP TABLE IF EXISTS role_permissions")
    op.execute("DROP TABLE IF EXISTS permissions")
    op.execute("DROP TABLE IF EXISTS roles")
    op.execute("DROP TABLE IF EXISTS audit_log_2026")
    op.execute("DROP TABLE IF EXISTS audit_log_2025")
    op.execute("DROP TABLE IF EXISTS audit_log")
