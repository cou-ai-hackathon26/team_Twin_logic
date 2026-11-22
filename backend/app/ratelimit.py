"""Tiny in-memory per-login rate limiter (one server process, so memory is enough)."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException

_lock = threading.Lock()
_hits: dict[tuple[str, int], deque] = defaultdict(deque)


def check(kind: str, user_id: int, limit: int, window_sec: float = 600.0) -> None:
    """Raise 429 when this login did `kind` more than `limit` times in the last window."""
    if limit <= 0:
        return
    now = time.monotonic()
    with _lock:
        q = _hits[(kind, user_id)]
        while q and now - q[0] > window_sec:
            q.popleft()
        if len(q) >= limit:
            wait = int(window_sec - (now - q[0])) // 60 + 1
            raise HTTPException(429, f"Too many attempts. Please wait about {wait} minute{'s' if wait > 1 else ''}.")
        q.append(now)


def reset() -> None:
    with _lock:
        _hits.clear()
