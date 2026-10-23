
"""
DocumentChunk ORM model + indexer.

Note on the Vector column: pgvector provides a Vector type via SQLAlchemy.
The vector dimension is configured in application settings (384 for bge-small).
Alembic migration 0003 defines the initial document_chunks table.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional, Sequence

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    ForeignKey,
    Integer,
    String,
    Text,
    text as sql_text,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import get_settings
from app.database.base import Base
from app.rag.vector_store.base import VectorRecord, VectorStore
from app.rag.vector_store.pgvector_store import PgvectorStore


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    chunk_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )

    document_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("documents.document_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    owner_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )

    sequence: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    embedding = mapped_column(
        Vector(get_settings().embedding_dimensions),
        nullable=False,
    )

    page: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )

    metadata_: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        "metadata",
        JSON,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=sql_text("NOW()"),
    )


class Indexer:
    """Writes parsed chunks and their embeddings to the vector store."""

    def __init__(self, session: AsyncSession):
        self._session = session
        self._store: VectorStore = PgvectorStore(session)

    async def index_chunks(self, records: Sequence[VectorRecord]) -> int:
        """Idempotent upsert: replace all chunks for each affected document."""
        count = await self._store.upsert(records)
        return count


async def delete_document_chunks(
    session: AsyncSession,
    document_id: str,
) -> int:
    """Delete all chunks for a document."""
    store = PgvectorStore(session)
    return await store.delete_by_document(document_id)
