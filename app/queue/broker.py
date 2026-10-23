"""
Taskiq broker (Redis-backed).

Two key design choices:
1. The broker is shared between the API process (enqueuing tasks) and the
   worker process (consuming tasks). Both import this module.
2. The broker is created lazily so the API can boot even if Redis is
   temporarily down (enqueue will fail, but other endpoints still work).
"""

from __future__ import annotations

from taskiq import TaskiqScheduler
from taskiq_redis import RedisAsyncResultBackend, ListQueueBroker

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger(__name__)

_broker: ListQueueBroker | None = None
_result_backend: RedisAsyncResultBackend | None = None


def get_broker() -> ListQueueBroker:
    global _broker
    if _broker is None:
        settings = get_settings()
        _broker = ListQueueBroker(url=settings.redis_url)
        _result_backend = RedisAsyncResultBackend(redis_url=settings.redis_url)
        _broker.with_result_backend(_result_backend)
        log.info("taskiq_broker_created", redis=settings.redis_url)
    return _broker


def get_result_backend() -> RedisAsyncResultBackend:
    if _result_backend is None:
        get_broker()
    assert _result_backend is not None
    return _result_backend


# Module-level broker instance — required by Taskiq's decorator approach.
broker = get_broker()