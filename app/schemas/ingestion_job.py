"""
Ingestion job schemas.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.common import ORMModel


class IngestionJobBase(ORMModel):
    job_id: str
    document_id: str
    queue_job_id: Optional[str] = None
    status: str
    attempt_count: int = 0
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class IngestionJobResponse(IngestionJobBase):
    pass


class IngestionJobListResponse(BaseModel):
    items: list[IngestionJobResponse]
    total: int