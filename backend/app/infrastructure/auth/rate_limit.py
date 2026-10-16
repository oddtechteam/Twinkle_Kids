"""In-process sliding-window rate limiter.

Scope: one API process. That suits a single-instance deployment (the initial plan). When the
API runs on several instances, swap this adapter for a shared store (Redis) or enforce limits at
the edge (CDN/WAF) — the RateLimiter port stays the same.
"""

import math
import time
from collections import deque
from collections.abc import Callable
from threading import Lock

MAX_TRACKED_KEYS = 50_000


class InMemoryRateLimiter:
    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._hits: dict[str, deque[float]] = {}
        self._lock = Lock()
        self._clock = clock

    def hit(self, key: str, *, limit: int, window_seconds: int) -> int | None:
        now = self._clock()
        with self._lock:
            if len(self._hits) > MAX_TRACKED_KEYS:
                self._evict(now, window_seconds)
            hits = self._hits.setdefault(key, deque())
            while hits and hits[0] <= now - window_seconds:
                hits.popleft()
            if len(hits) >= limit:
                return max(1, math.ceil(hits[0] + window_seconds - now))
            hits.append(now)
            return None

    def reset(self, key: str) -> None:
        with self._lock:
            self._hits.pop(key, None)

    def _evict(self, now: float, window_seconds: int) -> None:
        stale = [k for k, v in self._hits.items() if not v or v[-1] <= now - window_seconds]
        for key in stale:
            del self._hits[key]
