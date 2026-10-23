"""
Pre-download the embedding model so the worker doesn't stall on first use.

Usage:
    python scripts/download_embedding_model.py

Downloads to EMBEDDING_CACHE_DIR. Run this once on each host that runs
the worker (or build it into the Docker image).
"""

from __future__ import annotations

import sys

from app.core.config import get_settings


def main() -> None:
    settings = get_settings()
    print(f"Downloading embedding model: {settings.embedding_model}")
    print(f"Cache dir: {settings.embedding_cache_dir}")
    print("This may take a while (bge-small is ~130MB)...")

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print("ERROR: sentence-transformers not installed", file=sys.stderr)
        sys.exit(1)

    model = SentenceTransformer(
        settings.embedding_model,
        device=settings.embedding_device,
        cache_folder=settings.embedding_cache_dir,
    )
    # Sanity check dimensions
    vec = model.encode(["hello world"])[0]
    print(f"Done. Model produces {len(vec)}-dimensional vectors.")
    if len(vec) != settings.embedding_dimensions:
        print(
            f"WARNING: actual dimension ({len(vec)}) does not match "
            f"EMBEDDING_DIMENSIONS ({settings.embedding_dimensions}). "
            "Update .env and rebuild the schema.",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()