"""
Aggregates all v1 routers. Endpoints are added incrementally per phase.

Each sub-router is mounted under a stable prefix so the public URL space is
predictable:
    /api/v1/health
    /api/v1/documents
    /api/v1/ingestion-jobs
    /api/v1/retrieval
    /api/v1/chat
    /api/v1/tools
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.api.v1.documents import router as documents_router
from app.api.v1.ingestion_jobs import router as ingestion_jobs_router
from app.api.v1.retrieval import router as retrieval_router
from app.api.v1.chat import router as chat_router
from app.api.v1.conversations import router as conversations_router
from app.api.v1.tools import router as tools_router

router = APIRouter()
router.include_router(health_router, prefix="/health", tags=["health"])
router.include_router(documents_router, prefix="/documents", tags=["documents"])
router.include_router(ingestion_jobs_router, prefix="/ingestion-jobs", tags=["ingestion"])
router.include_router(retrieval_router, prefix="/retrieval", tags=["retrieval"])
router.include_router(chat_router, prefix="/chat", tags=["chat"])
router.include_router(conversations_router, prefix="/chat/conversations", tags=["conversations"])
router.include_router(tools_router, prefix="/tools", tags=["tools"])