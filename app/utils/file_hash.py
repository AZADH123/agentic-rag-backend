"""SHA-256 content hashing for deduplication."""

from __future__ import annotations

import hashlib
from pathlib import Path


def compute_file_hash(path: Path | str, chunk_size: int = 1 << 16) -> str:
    """Stream a file and return its hex SHA-256 digest."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def compute_bytes_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()