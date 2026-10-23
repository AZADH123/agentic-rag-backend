"""create document_chunks with pgvector

Revision ID: 0003_document_chunks
Revises: 0002_ingestion_jobs
Create Date: 2025-01-01 00:02:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_document_chunks"
down_revision = "0002_ingestion_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # NOTE: embedding dimension is hardcoded to 384 to match bge-small-en-v1.5.
    # If you switch to a larger embedding model, you MUST re-create this column
    # (the vector type is fixed-size in pgvector).
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    op.create_table(
        "document_chunks",
        sa.Column("chunk_id", sa.String(64), primary_key=True),
        sa.Column("document_id", sa.String(64),
                  sa.ForeignKey("documents.document_id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("owner_id", sa.String(128), nullable=False, index=True),
        sa.Column("sequence", sa.Integer, nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding", sa.dialects.postgresql.ARRAY(sa.Float), nullable=False),  # placeholder, replaced below
        sa.Column("page", sa.Integer, nullable=True),
        sa.Column("metadata", sa.JSON, nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Replace the FLOAT[] placeholder with the real VECTOR(384) type.
    op.execute("ALTER TABLE document_chunks DROP COLUMN embedding;")
    op.execute("ALTER TABLE document_chunks ADD COLUMN embedding vector(384) NOT NULL;")

    # HNSW index for fast ANN search using cosine distance.
    # HNSW doesn't require a separate training step (unlike IVFFlat) and works
    # well up to ~1M vectors. For larger scale, consider IVFFlat with explicit
    # lists tuning.
    op.execute(
        "CREATE INDEX document_chunks_embedding_idx "
        "ON document_chunks USING hnsw (embedding vector_cosine_ops);"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS document_chunks_embedding_idx;")
    op.drop_table("document_chunks")