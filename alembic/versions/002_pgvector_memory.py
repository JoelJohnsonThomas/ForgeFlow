"""002 — PGVector memory: memory_vectors (dim=1536) + agent_knowledge (hybrid FTS+vector).

Revision ID: 002
Revises: 001
Create Date: 2026-05-19
"""


from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ------------------------------------------------------------------ #
    # memory_vectors — semantic memory with cosine similarity             #
    # ------------------------------------------------------------------ #
    op.execute("""
        CREATE TABLE memory_vectors (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            namespace   VARCHAR(128) NOT NULL DEFAULT 'default',
            content     TEXT NOT NULL,
            embedding   vector(1536),
            metadata    JSONB NOT NULL DEFAULT '{}',
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            expires_at  TIMESTAMPTZ
        )
    """)

    # ivfflat index for approximate nearest neighbor (fast for <1M rows)
    op.execute("""
        CREATE INDEX idx_memory_vectors_embedding
        ON memory_vectors USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
    """)
    op.execute("CREATE INDEX idx_memory_vectors_namespace ON memory_vectors(namespace)")
    op.execute("CREATE INDEX idx_memory_vectors_expires ON memory_vectors(expires_at) WHERE expires_at IS NOT NULL")

    # ------------------------------------------------------------------ #
    # agent_knowledge — hybrid full-text + vector search                  #
    # ------------------------------------------------------------------ #
    op.execute("""
        CREATE TABLE agent_knowledge (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            agent_name  VARCHAR(64) NOT NULL,
            fact_type   VARCHAR(64) NOT NULL,
            content     TEXT NOT NULL,
            embedding   vector(1536),
            fts_vector  TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
            metadata    JSONB NOT NULL DEFAULT '{}',
            confidence  NUMERIC(4,3) NOT NULL DEFAULT 1.0,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("""
        CREATE INDEX idx_agent_knowledge_embedding
        ON agent_knowledge USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 50)
    """)
    op.execute("CREATE INDEX idx_agent_knowledge_fts ON agent_knowledge USING GIN(fts_vector)")
    op.execute("CREATE INDEX idx_agent_knowledge_agent ON agent_knowledge(agent_name)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS agent_knowledge")
    op.execute("DROP TABLE IF EXISTS memory_vectors")
    op.execute("DROP EXTENSION IF EXISTS vector")
