"""
Document endpoints.

POST   /documents/upload             — upload + queue ingestion
GET    /documents                    — list (owner-scoped)
GET    /documents/{document_id}     — get one
DELETE /documents/{document_id}      — delete source + chunks + job records
POST   /documents/{document_id}/reindex — re-enqueue ingestion
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidFileError
from app.core.logging import get_logger
from app.dependencies import get_current_owner, get_session
from app.modules.documents.service import DocumentService
from app.schemas.document import (
    DocumentListResponse,
    DocumentResponse,
    DocumentReindexResponse,
    DocumentUploadResponse,
)

log = get_logger(__name__)
router = APIRouter()


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_document(
    file: UploadFile = File(..., description="PDF, DOCX, or TXT. See MAX_UPLOAD_SIZE_MB."),
    session: AsyncSession = Depends(get_session),
    owner: str = Depends(get_current_owner),
):
    """Upload a source document and queue asynchronous ingestion."""
    # UploadFile.file is a SpooledTemporaryFile — read fully into memory.
    # For huge files, stream directly to S3 instead.
    data = await file.read()
    if not data:
        raise InvalidFileError("Empty file")

    service = DocumentService(session)
    doc, queue_job_id = await service.upload_and_enqueue(
        filename=file.filename or "upload.bin",
        content_type=file.content_type or "application/octet-stream",
        data=data,
        owner_id=owner,
    )

    return DocumentUploadResponse(
        document_id=doc.document_id,
        job_id=queue_job_id or "",
        filename=doc.filename,
        status=doc.status,
    )


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
    owner: str = Depends(get_current_owner),
):
    service = DocumentService(session)
    items, total = await service.list(owner, limit=limit, offset=offset)
    return DocumentListResponse(
        items=[DocumentResponse.model_validate(d) for d in items],
        total=total,
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    session: AsyncSession = Depends(get_session),
    owner: str = Depends(get_current_owner),
):
    service = DocumentService(session)
    doc = await service.get(document_id, owner)
    return DocumentResponse.model_validate(doc)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    session: AsyncSession = Depends(get_session),
    owner: str = Depends(get_current_owner),
):
    service = DocumentService(session)
    await service.delete(document_id, owner)
    return None


@router.post(
    "/{document_id}/reindex",
    response_model=DocumentReindexResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def reindex_document(
    document_id: str,
    session: AsyncSession = Depends(get_session),
    owner: str = Depends(get_current_owner),
):
    service = DocumentService(session)
    doc, job_id = await service.reindex(document_id, owner)
    return DocumentReindexResponse(
        document_id=doc.document_id,
        job_id=job_id or "",
        status=doc.status,
    )