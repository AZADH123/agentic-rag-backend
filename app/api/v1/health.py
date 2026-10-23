"""
Health endpoints.

GET /health         — liveness probe. Cheap: returns 200 if the process is up.
GET /health/ready    — readiness probe. Pings DB, Redis, S3 (if available).

The readiness check is intentionally read-only and never exposes credentials
or internal config — it only reports each dependency as "ok"/"degraded".
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session

router = APIRouter()


@router.get("", status_code=status.HTTP_200_OK)
async def liveness() -> dict:
    """Process is alive. No dependency checks — used by k8s liveness probes."""
    return {"status": "ok"}


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness(session: AsyncSession = Depends(get_db_session)) -> dict:
    """
    Check required dependencies.

    Returns per-component status. If anything fails, we still return 200 but
    with status "degraded" so the probe can route traffic accordingly.
    """
    components: dict[str, str] = {}

    # Database + pgvector
    try:
        await session.execute(text("SELECT 1"))
        components["database"] = "ok"
        try:
            row = (await session.execute(
                text("SELECT extname FROM pg_extension WHERE extname='vector'")
            )).scalar_one_or_none()
            components["pgvector"] = "ok" if row else "missing"
        except Exception:
            components["pgvector"] = "missing"
    except Exception:
        components["database"] = "degraded"

    # Redis
    try:
        import redis.asyncio as aioredis
        from app.core.config import get_settings
        settings = get_settings()
        client = aioredis.from_url(settings.redis_url)
        await client.ping()
        await client.aclose()
        components["redis"] = "ok"
    except Exception:
        components["redis"] = "degraded"

    # S3 / MinIO — optional until Phase 2 lands the storage module.
    try:
        from app.storage.s3_client import get_s3_client  # type: ignore
        from app.core.config import get_settings
        s3 = get_s3_client()
        bucket = get_settings().s3_bucket_name
        s3.head_bucket(Bucket=bucket)
        components["storage"] = "ok"
    except ImportError:
        components["storage"] = "not_configured"
    except Exception:
        components["storage"] = "degraded"

    overall = "ok" if all(v == "ok" for v in components.values()) else "degraded"
    return {"status": overall, "components": components}