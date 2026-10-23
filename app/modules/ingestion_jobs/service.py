"""
Ingestion job service — public operations exposed to the API layer.

Key flows:
- get/list: trivial pass-throughs to the repository.
- retry: re-enqueue an existing failed job (or create a fresh one).
"""

from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import JobNotFoundError
from app.core.logging import get_logger
from app.modules.ingestion_jobs.models import IngestionJob
from app.modules.ingestion_jobs.repository import IngestionJobRepository

log = get_logger(__name__)


class IngestionJobService:
    def __init__(self, session: AsyncSession):
        self._session = session
        self._repo = IngestionJobRepository(session)

    async def get(self, job_id: str) -> IngestionJob:
        job = await self._repo.get(job_id)
        if job is None:
            raise JobNotFoundError(f"Ingestion job {job_id} not found")
        return job

    async def list(self, limit: int = 50, offset: int = 0) -> tuple[Sequence[IngestionJob], int]:
        return await self._repo.list(limit=limit, offset=offset)

    async def list_by_document(self, document_id: str) -> Sequence[IngestionJob]:
        return await self._repo.list_by_document(document_id)

    async def retry(self, job_id: str) -> IngestionJob:
        """Re-enqueue a failed job. Bumps attempt_count."""
        job = await self.get(job_id)

        if job.status not in ("failed", "queued"):
            # Idempotency: don't retry an already-running job.
            log.info("retry_skipped", job_id=job_id, current_status=job.status)
            return job

        from app.core.config import get_settings
        settings = get_settings()

        if job.attempt_count >= settings.task_max_retries:
            log.warning("retry_exhausted", job_id=job_id, attempts=job.attempt_count)
            # Mark failed permanently with a clear error.
            await self._repo.mark_failed(
                job_id,
                f"Max retries ({settings.task_max_retries}) exhausted.",
            )
            return await self.get(job_id)

        await self._repo.increment_attempt(job_id)
        await self._repo.mark_retrying(job_id)

        # Re-enqueue the worker task. If this fails, the row stays in
        # status='retrying' which a human can investigate.
        from app.queue.tasks import process_document_task
        try:
            task = await process_document_task.kiq(job.document_id, job_id)
            await self._repo.set_queue_job_id(job_id, task.task_id)
            log.info("retry_enqueued", job_id=job_id, queue_task_id=task.task_id)
        except Exception as e:
            log.error("retry_enqueue_failed", job_id=job_id, error=str(e))
            await self._repo.mark_failed(job_id, f"Retry enqueue failed: {e}")

        return await self.get(job_id)