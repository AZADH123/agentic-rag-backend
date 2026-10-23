"""create conversations and messages tables

Revision ID: 0004_conversations
Revises: 0003_document_chunks
Create Date: 2025-01-01 00:03:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004_conversations"
down_revision = "0003_document_chunks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("conversation_id", sa.String(64), primary_key=True),
        sa.Column("owner_id", sa.String(128), nullable=False, index=True),
        sa.Column("title", sa.String(256), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "messages",
        sa.Column("message_id", sa.String(64), primary_key=True),
        sa.Column("conversation_id", sa.String(64),
                  sa.ForeignKey("conversations.conversation_id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("citations", sa.JSON, nullable=True),
        sa.Column("tool_calls", sa.JSON, nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_messages_conversation_created", "messages",
                    ["conversation_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_messages_conversation_created", table_name="messages")
    op.drop_table("messages")
    op.drop_table("conversations")