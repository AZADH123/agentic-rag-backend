"""
Ingestion job endpoints.

GET   /ingestion-jobs                 — list all jobs
GET   /ingestion-jobs/{job_id}        — get one job
POST  /ingestion-jobs/{job_id}/retry  — re-enqueue a failed job
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_owner, get_session
from app.modules.ingestion_jobs.service import IngestionJobService
from app.schemas.ingestion_job import (
    IngestionJobListResponse,
    IngestionJobResponse,
)

router = APIRouter()


@router.get("", response_model=IngestionJobListResponse)
async def list_jobs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
    owner: str = Depends(get_current_owner),
):
    service = IngestionJobService(session)
    items, total = await service.list(limit=limit, offset=offset)
    return IngestionJobListResponse(
        items=[IngestionJobResponse.model_validate(j) for j in items],
        total=total,
    )


@router.get("/{job_id}", response_model=IngestionJobResponse)
async def get_job(
    job_id: str,
    session: AsyncSession = Depends(get_session),
    owner: str = Depends(get_current_owner),
):
    service = IngestionJobService(session)
    job = await service.get(job_id)
    return IngestionJobResponse.model_validate(job)


@router.post("/{job_id}/retry", response_model=IngestionJobResponse,
             status_code=status.HTTP_202_ACCEPTED)
async def retry_job(
    job_id: str,
    session: AsyncSession = Depends(get_session),
    owner: str = Depends(get_current_owner),
):
    service = IngestionJobService(session)
    job = await service.retry(job_id)
    return IngestionJobResponse.model_validate(job)