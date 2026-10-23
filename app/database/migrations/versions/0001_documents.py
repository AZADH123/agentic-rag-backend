"""create documents table

Revision ID: 0001_documents
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0001_documents"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    op.create_table(
        "documents",
        sa.Column("document_id", sa.String(64), primary_key=True),
        sa.Column("owner_id", sa.String(128), nullable=False, index=True),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("content_type", sa.String(255), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger, nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=True, index=True),
        sa.Column("s3_key", sa.String(1024), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, index=True, server_default="uploaded"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("documents")