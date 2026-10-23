"""
Document schemas (request/response contracts for /documents endpoints).
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class DocumentBase(ORMModel):
    document_id: str = Field(..., description="Unique document identifier (doc_<ulid>)")
    filename: str
    content_type: str
    file_size_bytes: int
    content_hash: Optional[str] = None
    owner_id: str
    status: str
    error: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class DocumentResponse(DocumentBase):
    s3_key: Optional[str] = None  # hidden in production; useful in dev


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int


class DocumentUploadResponse(BaseModel):
    """Returned by POST /documents/upload when file is stored + job enqueued."""
    document_id: str
    job_id: str
    filename: str
    status: str = "queued"


class DocumentReindexResponse(BaseModel):
    document_id: str
    job_id: str
    status: str = "queued"
