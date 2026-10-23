"""
Document service — orchestrates upload, status transitions, deletion.

This is where business logic lives. The service coordinates:
- File validation
- Hashing for dedup
- S3 upload
- DB record creation
- Queue job submission (delegated to ingestion_jobs service in Phase 3)

Key reliability concern: S3 upload, DB commit, and queue enqueue are NOT
atomic. We order operations so that a failure between steps leaves the
system in a recoverable state:
  1. Upload to S3 → if this fails, nothing else happened, client retries.
  2. Insert DB row with status='uploaded' → if S3 succeeded but DB fails,
     we have an orphaned S3 object. Acceptable; can be GC'd later.
  3. Enqueue job → if this fails, update DB to status='queued' fails and
     we record status='failed' with error. User can retry via /reindex.

Dedup: if a file with identical content_hash + owner_id exists, we return
the existing document (and trigger a reindex if its status is 'failed').
"""

from __future__ import annotations

import io
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import DocumentNotFoundError, InvalidFileError
from app.core.logging import get_logger
from app.modules.documents.models import Document
from app.modules.documents.repository import DocumentRepository
from app.modules.documents.validators import (
    validate_content_type,
    validate_filename,
    validate_size,
)
from app.storage.object_storage import get_object_storage
from app.storage.storage_keys import build_source_key, new_document_id
from app.utils.file_hash import compute_bytes_hash

log = get_logger(__name__)


class DocumentService:
    def __init__(self, session: AsyncSession):
        self._session = session
        self._repo = DocumentRepository(session)
        self._storage = get_object_storage()

    async def upload_and_enqueue(
        self,
        *,
        filename: str,
        content_type: str,
        data: bytes,
        owner_id: str,
    ) -> tuple[Document, Optional[str]]:
        """
        Validate, store, persist, and enqueue ingestion.

        Returns (document, queue_job_id_or_None).

        If a duplicate (same hash + owner) already exists, returns the
        existing document (no re-upload) — caller can decide what to do.
        """
        settings = get_settings()
        ext = validate_filename(filename)
        validate_content_type(content_type, ext)
        validate_size(len(data))

        content_hash = compute_bytes_hash(data)

        # Dedup: same owner, same hash → return existing
        existing = await self._repo.find_by_hash(content_hash, owner_id)
        if existing is not None:
            log.info("document_dedup_hit",
                     document_id=existing.document_id,
                     content_hash=content_hash)
            return existing, None

        # New document
        document_id = new_document_id()
        s3_key = build_source_key(document_id, filename)

        # 1. Upload to S3
        self._storage.upload_bytes(s3_key, data, content_type)
        log.info("s3_uploaded", key=s3_key, size=len(data))

        # 2. Persist DB row (status: uploaded)
        doc = Document(
            document_id=document_id,
            owner_id=owner_id,
            filename=filename,
            content_type=content_type,
            file_size_bytes=len(data),
            content_hash=content_hash,
            s3_key=s3_key,
            status="uploaded",
        )
        await self._repo.create(doc)
        await self._session.flush()
        await self._session.commit()
        log.info("document_persisted", document_id=document_id)

        # 3. Enqueue ingestion job (added in Phase 3). For now, just leave
        #    the document in status='uploaded' and return None for job_id.
        queue_job_id: Optional[str] = None
        try:
            from app.queue.tasks import enqueue_ingestion
            queue_job_id = await enqueue_ingestion(document_id=document_id)
            await self._repo.update_status(document_id, "queued")
            log.info("document_queued", document_id=document_id, job_id=queue_job_id)
        except ImportError:
            # Phase 2 only — queue module not yet built. Leave as 'uploaded'.
            log.debug("queue_not_available_yet")
        except Exception as e:
            log.error("enqueue_failed", document_id=document_id, error=str(e))
            await self._repo.update_status(document_id, "failed",
                                            error=f"enqueue failed: {e}")
            # Don't re-raise: the upload itself succeeded. Caller will see
            # status='failed' and can retry via /reindex.

        return doc, queue_job_id

    async def get(self, document_id: str, owner_id: str) -> Document:
        doc = await self._repo.get(document_id)
        if doc is None:
            raise DocumentNotFoundError(f"Document {document_id} not found")
        if doc.owner_id != owner_id:
            # Don't leak existence — return 404 instead of 403.
            raise DocumentNotFoundError(f"Document {document_id} not found")
        return doc

    async def list(self, owner_id: str, limit: int = 50, offset: int = 0) -> tuple[list[Document], int]:
        return await self._repo.list_by_owner(owner_id, limit, offset)

    async def list_all(self, limit: int = 50, offset: int = 0) -> tuple[list[Document], int]:
        """Admin view — for local dev when auth is off."""
        return await self._repo.list_all(limit, offset)

    async def delete(self, document_id: str, owner_id: str) -> None:
        doc = await self.get(document_id, owner_id)
        # Mark deleting first so a concurrent worker can see the tombstone.
        await self._repo.update_status(document_id, "deleting")

        # Delete S3 prefix (covers source + any derived objects).
        from app.storage.storage_keys import build_chunk_prefix
        prefix = build_chunk_prefix(document_id)
        try:
            deleted_count = self._storage.delete_prefix(prefix)
            log.info("s3_prefix_deleted", prefix=prefix, count=deleted_count)
        except Exception as e:
            log.error("s3_delete_failed", document_id=document_id, error=str(e))
            # Continue with DB delete — don't leave orphaned metadata.

        # Delete chunks/vectors (added in Phase 4 — guarded with try/except).
        try:
            from app.rag.indexing.indexer import delete_document_chunks
            await delete_document_chunks(self._session, document_id)
        except ImportError:
            pass

        # Delete ingestion jobs for this document (added in Phase 3).
        try:
            from app.modules.ingestion_jobs.repository import IngestionJobRepository
            job_repo = IngestionJobRepository(self._session)
            await job_repo.delete_by_document(document_id)
        except ImportError:
            pass

        # Finally, delete the document row.
        await self._repo.delete(document_id)
        log.info("document_deleted", document_id=document_id)

    async def reindex(self, document_id: str, owner_id: str) -> tuple[Document, Optional[str]]:
        """Re-enqueue ingestion for an existing document."""
        doc = await self.get(document_id, owner_id)
        if doc.status == "processing":
            raise InvalidFileError("Document is already being processed")

        queue_job_id: Optional[str] = None
        try:
            from app.queue.tasks import enqueue_ingestion
            queue_job_id = await enqueue_ingestion(document_id=document_id)
            await self._repo.update_status(document_id, "queued")
            log.info("document_reindexed", document_id=document_id, job_id=queue_job_id)
        except ImportError:
            log.debug("queue_not_available_yet")
        except Exception as e:
            log.error("reindex_failed", document_id=document_id, error=str(e))
            await self._repo.update_status(document_id, "failed", error=str(e))

        return doc, queue_job_id