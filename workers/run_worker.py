"""
Standalone Taskiq worker entrypoint.

Run with:
    python workers/run_worker.py

This process imports the broker, registers all task definitions (just by
importing app.queue.tasks), and blocks on broker consumption.

IMPORTANT: the worker shares the SAME code as the API but runs in its own
process. It must NEVER be run inside the API process — that would defeat
the purpose of offloading heavy work (embeddings, parsing) from request
handlers.
"""

from __future__ import annotations

import asyncio
import signal
import sys
from pathlib import Path

# Ensure project root is in sys.path when executed directly
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger

log = get_logger(__name__)


async def main() -> None:
    configure_logging()
    settings = get_settings()
    log.info("worker_starting", env=settings.app_env, concurrency=settings.worker_concurrency)

    # Importing the tasks module registers @broker.task decorators.
    from app.queue.broker import broker
    import app.queue.tasks  # noqa: F401

    # Database engine for worker-side persistence.
    from app.database.session import init_db
    init_db()

    await broker.startup()

    # Block until shutdown signal.
    stop_event = asyncio.Event()

    def _signal_handler(*_: object) -> None:
        log.info("shutdown_signal_received")
        stop_event.set()

    try:
        signal.signal(signal.SIGINT, _signal_handler)
        signal.signal(signal.SIGTERM, _signal_handler)
    except (ValueError, AttributeError):
        pass

    from taskiq.receiver import Receiver
    receiver = Receiver(
        broker=broker,
        max_async_tasks=settings.worker_concurrency,
    )
    log.info("worker_listening", broker="redis")
    await receiver.listen(stop_event)

    log.info("worker_shutting_down")
    await broker.shutdown()
    log.info("worker_stopped")


if __name__ == "__main__":
    import sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(
            asyncio.WindowsProactorEventLoopPolicy()
        )
    asyncio.run(main())