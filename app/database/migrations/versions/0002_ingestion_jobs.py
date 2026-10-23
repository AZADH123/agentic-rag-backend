"""create ingestion_jobs table

Revision ID: 0002_ingestion_jobs
Revises: 0001_documents
Create Date: 2025-01-01 00:01:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_ingestion_jobs"
down_revision = "0001_documents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ingestion_jobs",
        sa.Column("job_id", sa.String(64), primary_key=True),
        sa.Column("document_id", sa.String(64),
                  sa.ForeignKey("documents.document_id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("queue_job_id", sa.String(256), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, index=True, server_default="queued"),
        sa.Column("attempt_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_ingestion_jobs_document_id_status", "ingestion_jobs",
                    ["document_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_ingestion_jobs_document_id_status", table_name="ingestion_jobs")
    op.drop_table("ingestion_jobs")