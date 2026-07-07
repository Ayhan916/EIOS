"""101 — historical knowledge base

Phase 4: Lernt aus Vergangenheit — Ereignis → Gegenmassnahme → Wirkung.
Verknüpft intelligence_timeline_events + findings + CAPs + health_score_delta.
Embeddings mit multilingual-e5-large (1024 dims) für semantische Suche.
"""

from alembic import op
import sqlalchemy as sa

revision = "101"
down_revision = "100"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "historical_knowledge",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False, index=True),
        sa.Column("supplier_id", sa.String(36), nullable=True, index=True),
        sa.Column("event_description", sa.Text, nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False, server_default=""),
        sa.Column("event_severity", sa.String(20), nullable=True),
        sa.Column("countermeasure_description", sa.Text, nullable=False, server_default=""),
        sa.Column("countermeasure_type", sa.String(50), nullable=False, server_default=""),
        sa.Column("outcome_description", sa.Text, nullable=False, server_default=""),
        sa.Column("outcome_category", sa.String(30), nullable=False, server_default="unknown"),
        sa.Column("health_delta", sa.Float, nullable=True),
        sa.Column("csddd_right", sa.String(50), nullable=True, index=True),
        sa.Column("twin_dimension", sa.String(50), nullable=True),
        sa.Column("content_text", sa.Text, nullable=False),
        sa.Column("source_event_id", sa.String(36), nullable=True, index=True),
        sa.Column("source_finding_id", sa.String(36), nullable=True, index=True),
        sa.Column("source_cap_id", sa.String(36), nullable=True, index=True),
        sa.Column("reference_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )

    # Embedding-Spalte als echten pgvector Vector(1024)
    op.execute("ALTER TABLE historical_knowledge ADD COLUMN embedding vector(1024)")

    # HNSW-Index für cosine similarity
    op.execute("""
        CREATE INDEX ix_hk_embedding_hnsw
        ON historical_knowledge
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)

    # Partielle Unique Constraints via raw SQL (SQLAlchemy ORM unterstützt postgresql_where nicht)
    op.execute("""
        CREATE UNIQUE INDEX uq_hk_event
        ON historical_knowledge (organization_id, source_event_id)
        WHERE source_event_id IS NOT NULL
    """)
    op.execute("""
        CREATE UNIQUE INDEX uq_hk_cap
        ON historical_knowledge (organization_id, source_cap_id)
        WHERE source_cap_id IS NOT NULL
    """)

    op.create_index("ix_hk_org_right",    "historical_knowledge", ["organization_id", "csddd_right"])
    op.create_index("ix_hk_supplier_date", "historical_knowledge", ["supplier_id", "reference_date"])


def downgrade() -> None:
    op.drop_table("historical_knowledge")
