
"""
Document ORM model.

A Document row is the durable record of one uploaded source file. It tracks:
- identity (id, owner, filename)
- storage (S3 key, content type, size, hash for deduplication)
- lifecycle (status, error)
- timestamps

Status transitions (see service.py for the actual state machine):
    uploaded → queued → processing → indexed
                                       ↘ failed
                          ↘ retrying → processing
    (any) → deleting → deleted
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, String, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Document(Base):
    __tablename__ = "documents"

    # Unique document identifier
    document_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )

    # User who owns the document
    owner_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )

    # Original uploaded filename
    filename: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )

    # File MIME type, such as application/pdf
    content_type: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # File size in bytes
    file_size_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    # SHA-256 hash or another content fingerprint for deduplication
    content_hash: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )

    # S3 object storage key
    s3_key: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
    )

    # Document processing lifecycle status
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="uploaded",
        index=True,
    )

    # Error details if processing fails
    error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Record creation timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Record update timestamp
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
