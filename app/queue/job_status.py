"""
Status tracking helpers for ingestion jobs.

Redis is the queue infrastructure, NOT the source of truth for job status.
Postgres holds the durable job record; Redis is only used for:
- the task queue itself
- the result backend (return values / exceptions)

This module exposes pure-Python status constants so all layers agree on
the vocabulary.
"""

from __future__ import annotations


class JobStatus:
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class DocumentStatus:
    UPLOADED = "uploaded"
    QUEUED = "queued"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"
    RETRYING = "retrying"
    DELETING = "deleting"
    DELETED = "deleted"


ALLOWED_TRANSITIONS = {
    DocumentStatus.UPLOADED: {DocumentStatus.QUEUED, DocumentStatus.FAILED},
    DocumentStatus.QUEUED: {DocumentStatus.PROCESSING, DocumentStatus.FAILED, DocumentStatus.DELETING},
    DocumentStatus.PROCESSING: {DocumentStatus.INDEXED, DocumentStatus.FAILED, DocumentStatus.DELETING},
    DocumentStatus.FAILED: {DocumentStatus.QUEUED, DocumentStatus.RETRYING, DocumentStatus.DELETING},
    DocumentStatus.RETRYING: {DocumentStatus.PROCESSING, DocumentStatus.FAILED},
    DocumentStatus.INDEXED: {DocumentStatus.QUEUED, DocumentStatus.DELETING},  # allow reindex
    DocumentStatus.DELETING: {DocumentStatus.DELETED},
    DocumentStatus.DELETED: set(),
}


def can_transition(from_status: str, to_status: str) -> bool:
    return to_status in ALLOWED_TRANSITIONS.get(from_status, set())