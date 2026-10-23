"""
Common schema primitives used across endpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field


T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated list wrapper."""
    items: List[T]
    total: int
    limit: int
    offset: int


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ErrorDetail


class ORMModel(BaseModel):
    """Base for schemas that map to ORM models."""
    model_config = ConfigDict(from_attributes=True)


class TimestampMixin(BaseModel):
    created_at: datetime
    updated_at: Optional[datetime] = None