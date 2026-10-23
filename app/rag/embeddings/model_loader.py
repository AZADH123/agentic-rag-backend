"""
Singleton loader for the sentence-transformers model.

Loads the model ONCE per worker process (instead of once per document),
then caches it. Subsequent calls return the same instance.

Why a separate module instead of doing this inside BgeEmbeddings:
- The first .load() takes ~5-15s (model download + torch initialization).
  Doing this inside the constructor would block every test that constructs
  a BgeEmbeddings object.
- Centralized here, we can warm the cache at worker startup (see
  workers/run_worker.py) so the first ingestion task doesn't pay this cost.
"""

from __future__ import annotations

import threading
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger(__name__)

_model: Any | None = None
_lock = threading.Lock()


def get_model() -> Any:
    """Return the cached SentenceTransformer instance (loads on first call)."""
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                settings = get_settings()
                log.info("loading_embedding_model",
                         model=settings.embedding_model,
                         device=settings.embedding_device,
                         cache=settings.embedding_cache_dir)
                import contextlib
                import sys
                from sentence_transformers import SentenceTransformer
                with contextlib.redirect_stdout(sys.stderr):
                    _model = SentenceTransformer(
                        settings.embedding_model,
                        device=settings.embedding_device,
                        cache_folder=settings.embedding_cache_dir,
                    )
                    # Warm up the model with a tiny input so the first real
                    # request doesn't pay JIT/init cost.
                    _model.encode(["warmup"], batch_size=1, show_progress_bar=False)
                log.info("embedding_model_ready",
                         model=settings.embedding_model,
                         dimensions=_model.get_sentence_embedding_dimension())
    return _model


def reset_model() -> None:
    """Force re-load on next call (used in tests)."""
    global _model
    _model = None