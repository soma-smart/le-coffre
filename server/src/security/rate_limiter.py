"""In-memory sliding window rate limiter.

Used by :class:`RateLimitMiddleware` as the primary-adapter-adjacent store
for per-bucket request timestamps.  The caller passes the current datetime
on every check so the limiter never reads the clock itself — the middleware
obtains ``now`` from the shared-kernel ``TimeGateway`` and the integration
tests pass plain ``datetime`` literals instead of monkeypatching.
"""

from __future__ import annotations

import math
import threading
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True)
class RateLimitResult:
    is_limited: bool
    limit: int
    remaining: int
    retry_after: int


class InMemoryRateLimiter:
    """Thread-safe sliding-window rate limiter backed by an in-memory dict.

    Each key (e.g. ``ip:<addr>:api`` or ``user:<id>:api``) maintains a deque
    of request timestamps.  Requests older than the window are evicted on
    every check.
    """

    def __init__(self) -> None:
        self._requests: dict[str, deque[datetime]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, max_requests: int, window_seconds: int, now: datetime) -> RateLimitResult:
        """Record a request attempt at ``now`` and return whether it is limited."""
        window_start = now - timedelta(seconds=window_seconds)

        with self._lock:
            timestamps = self._requests[key]

            while timestamps and timestamps[0] <= window_start:
                timestamps.popleft()

            if len(timestamps) >= max_requests:
                retry_after = math.ceil((timestamps[0] - window_start).total_seconds())
                return RateLimitResult(
                    is_limited=True,
                    limit=max_requests,
                    remaining=0,
                    retry_after=retry_after,
                )

            timestamps.append(now)
            remaining = max_requests - len(timestamps)
            return RateLimitResult(
                is_limited=False,
                limit=max_requests,
                remaining=remaining,
                retry_after=0,
            )

    def reset(self) -> None:
        """Clear all tracked state. Testing helper."""
        with self._lock:
            self._requests.clear()
