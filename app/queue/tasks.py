"""
Taskiq tasks.

The single ingestion task:
- Receives only stable identifiers (document_id, job_id) — never file bytes.
- The worker downloads the file from S3 inside the task.
- Uses bounded retries with backoff (configured via settings.task_max_retries).

Idempotency:
- The ingestion pipeline (Phase 4) is idempotent: re-running it on the same
  document replaces existing chunks rather than duplicating them.
- We also set job status='processing' atomically before doing work so a
  duplicate dequeue won't run twice.

How to enqueue from anywhere:
    from app.queue.tasks import enqueue_ingestion
    job_id = await enqueue_ingestion(document_id="doc_123")
"""

from __future__ import annotations

from typing import Optional

from app.core.config import get_settings
from app.core.logging import get_logger
from app.queue.broker import broker
from app.utils.ids import new_id

log = get_logger(__name__)


@broker.task(
    task_name="ingestion.process_document",
    max_retries=None,  # we manage retries manually via DB state
    timeout=600,  # 10 minutes hard cap
)
async def process_document_task(document_id: str, job_id: str) -> dict:
    """
    The worker-side entry point. Returns a summary dict (used by the result
    backend for inspection; durable state lives in Postgres).
    """
    # Lazy import — avoids loading the whole RAG stack on every broker init.
    from app.workers.ingestion_worker import run_ingestion

    log.info("task_started", document_id=document_id, job_id=job_id)
    summary = await run_ingestion(document_id=document_id, job_id=job_id)
    log.info("task_finished", document_id=document_id, job_id=job_id,
             status=summary.get("status"))
    return summary


async def enqueue_ingestion(document_id: str) -> str:
    """
    Create a durable IngestionJob row in Postgres AND enqueue a Taskiq task.

    The Postgres row is created BEFORE the task is enqueued. If enqueue
    fails after the row is committed, the row remains in status='queued'
    and a periodic recovery job (or manual /retry) can re-enqueue it.

    Returns the job_id (string).
    """
    from app.database.session import db_session
    from app.modules.ingestion_jobs.models import IngestionJob
    from app.modules.ingestion_jobs.repository import IngestionJobRepository
    from app.queue.job_status import JobStatus
    from app.utils.ids import new_id as ulid

    job_id = ulid("job")

    async with db_session() as session:
        repo = IngestionJobRepository(session)
        job = IngestionJob(
            job_id=job_id,
            document_id=document_id,
            status=JobStatus.QUEUED,
            attempt_count=0,
        )
        await repo.create(job)

    # Now enqueue. If this fails, the job row stays as 'queued' with no
    # queue_job_id; the /retry endpoint can pick it up.
    settings = get_settings()
    try:
        task = await process_document_task.kiq(document_id, job_id)
        queue_task_id = task.task_id
        async with db_session() as session:
            repo = IngestionJobRepository(session)
            await repo.set_queue_job_id(job_id, queue_task_id)
        log.info("task_enqueued", job_id=job_id, queue_task_id=queue_task_id)
    except Exception as e:
        log.error("enqueue_failed", job_id=job_id, error=str(e))
        # Don't raise — the caller (document service) handles status update.

    return job_id