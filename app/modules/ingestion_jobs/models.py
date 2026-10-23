"""
IngestionJob ORM model.

A row is created whenever a document is queued for processing. It tracks:
- document_id (FK to documents)
- queue_job_id (the Taskiq task_id, used for cancellation/inspection)
- status, attempt_count, error, timestamps

Status transitions:
    queued → processing → completed
                          ↘ failed → retrying → processing → ...
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    job_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    document_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("documents.document_id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    queue_job_id: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued", index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        server_default=func.now(), onupdate=func.now(),
    )