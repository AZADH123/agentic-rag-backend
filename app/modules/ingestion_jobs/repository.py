"""
Ingestion job repository — DB access for ingestion_jobs.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Sequence

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ingestion_jobs.models import IngestionJob


class IngestionJobRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get(self, job_id: str) -> Optional[IngestionJob]:
        return await self._session.get(IngestionJob, job_id)

    async def list(self, limit: int = 50, offset: int = 0) -> tuple[Sequence[IngestionJob], int]:
        stmt = select(IngestionJob).order_by(IngestionJob.created_at.desc())
        items = (await self._session.execute(stmt.limit(limit).offset(offset))).scalars().all()
        total = (await self._session.execute(
            select(func.count()).select_from(IngestionJob)
        )).scalar_one()
        return items, total

    async def list_by_document(self, document_id: str) -> Sequence[IngestionJob]:
        stmt = select(IngestionJob).where(
            IngestionJob.document_id == document_id
        ).order_by(IngestionJob.created_at.desc())
        return (await self._session.execute(stmt)).scalars().all()

    async def create(self, job: IngestionJob) -> IngestionJob:
        self._session.add(job)
        await self._session.flush()
        return job

    async def set_queue_job_id(self, job_id: str, queue_job_id: str) -> None:
        await self._session.execute(
            update(IngestionJob).where(IngestionJob.job_id == job_id).values(
                queue_job_id=queue_job_id,
            )
        )

    async def mark_processing(self, job_id: str) -> None:
        await self._session.execute(
            update(IngestionJob).where(IngestionJob.job_id == job_id).values(
                status="processing",
                started_at=datetime.utcnow(),
            )
        )

    async def mark_completed(self, job_id: str) -> None:
        await self._session.execute(
            update(IngestionJob).where(IngestionJob.job_id == job_id).values(
                status="completed",
                completed_at=datetime.utcnow(),
                error=None,
            )
        )

    async def mark_failed(self, job_id: str, error: str) -> None:
        await self._session.execute(
            update(IngestionJob).where(IngestionJob.job_id == job_id).values(
                status="failed",
                error=error,
                completed_at=datetime.utcnow(),
            )
        )

    async def mark_retrying(self, job_id: str) -> None:
        await self._session.execute(
            update(IngestionJob).where(IngestionJob.job_id == job_id).values(
                status="retrying",
            )
        )

    async def increment_attempt(self, job_id: str) -> int:
        """Atomically bump attempt_count and return the new value."""
        stmt = (
            update(IngestionJob)
            .where(IngestionJob.job_id == job_id)
            .values(attempt_count=IngestionJob.attempt_count + 1)
            .returning(IngestionJob.attempt_count)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def delete_by_document(self, document_id: str) -> None:
        await self._session.execute(
            delete(IngestionJob).where(IngestionJob.document_id == document_id)
        )