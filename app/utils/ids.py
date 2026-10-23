"""ID generation. We use prefix + ULID for sortable, collision-resistant IDs."""

from __future__ import annotations

import time

# ULID implementation: 48-bit ms timestamp + 80-bit random.
import os


def _ulid() -> str:
    """Generate a 26-char ULID string (no external dep)."""
    ts = int(time.time() * 1000)
    rand = os.urandom(10)
    # Encode 16 bytes (8 ts + ... actually ULID uses 6 bytes ts + 10 random)
    ts_bytes = ts.to_bytes(6, "big")
    raw = ts_bytes + rand  # 16 bytes total
    # Crockford base32
    alphabet = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
    # Convert bytes -> big int -> base32 (26 chars)
    n = int.from_bytes(raw, "big")
    out = []
    for _ in range(26):
        n, r = divmod(n, 32)
        out.append(alphabet[r])
    return "".join(reversed(out))


def new_id(prefix: str) -> str:
    """Return e.g. 'doc_01HXYZ...'."""
    return f"{prefix}_{_ulid().lower()}"