"""
Ingestion worker entrypoint.

This is the function invoked by Taskiq when a `process_document_task` is
dequeued. It coordinates:
1. Mark the job as 'processing' in Postgres (atomic guard against double-exec).
2. Download the source file from S3.
3. Run the RAG ingestion pipeline (Phase 4) — parse, chunk, embed, index.
4. Update job + document status.
5. On failure, mark failed and let the retry endpoint handle re-enqueueing.

The pipeline is loaded lazily so this module can be imported even before
Phase 4 lands (the import is deferred until run_ingestion is called).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import anyio

from app.core.logging import get_logger
from app.database.session import db_session
from app.modules.documents.repository import DocumentRepository
from app.modules.ingestion_jobs.repository import IngestionJobRepository
from app.queue.job_status import DocumentStatus, JobStatus

log = get_logger(__name__)


async def run_ingestion(document_id: str, job_id: str) -> dict[str, Any]:
    """
    Execute ingestion for one document. Returns a summary dict.

    Idempotency note: if the same job_id is dequeued twice (Taskiq's at-least-
    once delivery), the second invocation will see status != 'queued' and
    skip — preventing duplicate indexing work.
    """
    summary: dict[str, Any] = {
        "document_id": document_id,
        "job_id": job_id,
        "status": "unknown",
    }

    async with db_session() as session:
        job_repo = IngestionJobRepository(session)
        doc_repo = DocumentRepository(session)

        # 1. Atomic transition queued → processing.
        job = await job_repo.get(job_id)
        if job is None:
            log.error("job_not_found", job_id=job_id)
            summary["status"] = "missing_job"
            return summary

        if job.status == JobStatus.PROCESSING:
            log.warning("job_already_running", job_id=job_id)
            summary["status"] = "already_running"
            return summary
        if job.status == JobStatus.COMPLETED:
            log.info("job_already_completed", job_id=job_id)
            summary["status"] = "completed"
            return summary

        await job_repo.mark_processing(job_id)
        await doc_repo.update_status(document_id, DocumentStatus.PROCESSING)

    # 2-3. Run pipeline OUTSIDE the DB transaction (long-running).
    try:
        # Load source from S3.
        from app.storage.object_storage import get_object_storage

        async with db_session() as session:
            doc_repo = DocumentRepository(session)
            doc = await doc_repo.get(document_id)
            if doc is None:
                raise RuntimeError(f"document {document_id} not found in DB")
            s3_key = doc.s3_key
            content_type = doc.content_type
            filename = doc.filename
            owner_id = doc.owner_id

        storage = get_object_storage()
        file_bytes = storage.download_bytes(s3_key)
        log.info("source_downloaded",
                 document_id=document_id, s3_key=s3_key, bytes=len(file_bytes))

        # Run the actual RAG ingestion pipeline (Phase 4).
        # Lazy import — pipeline import loads torch + sentence-transformers
        # which is expensive. Defer until actually needed.
        from app.rag.ingestion.pipeline import IngestionPipeline
        pipeline = IngestionPipeline()
        await pipeline.run(
            document_id=document_id,
            content_bytes=file_bytes,
            content_type=content_type,
            filename=filename,
            owner_id=owner_id,
        )

        # 4. Mark success.
        async with db_session() as session:
            job_repo = IngestionJobRepository(session)
            doc_repo = DocumentRepository(session)
            await job_repo.mark_completed(job_id)
            await doc_repo.update_status(document_id, DocumentStatus.INDEXED, error=None)

        summary["status"] = "completed"
        log.info("ingestion_completed", document_id=document_id, job_id=job_id)
        return summary

    except Exception as e:
        log.exception("ingestion_failed", document_id=document_id, job_id=job_id)
        # 5. Mark failed; expose truncated error message.
        error_msg = (str(e)[:500] if str(e) else e.__class__.__name__)
        async with db_session() as session:
            job_repo = IngestionJobRepository(session)
            doc_repo = DocumentRepository(session)
            await job_repo.mark_failed(job_id, error_msg)
            await doc_repo.update_status(document_id, DocumentStatus.FAILED, error=error_msg)
        summary["status"] = "failed"
        summary["error"] = error_msg
        return summary


def _content_type_for_document(doc: Any) -> str:
    """Pull content_type back from the doc object passed via closure."""
    return doc.content_type