"""In-memory sliding window rate limiter."""

import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass


@dataclass(frozen=True)
class RateLimitResult:
    is_limited: bool
    limit: int
    remaining: int
    retry_after: int


class InMemoryRateLimiter:
    """
    Thread-safe sliding window rate limiter backed by an in-memory dict.

    Each key (e.g. IP address or user ID) maintains a deque of request
    timestamps. Requests older than the window are evicted on every check.
    """

    def __init__(self) -> None:
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(
        self, key: str, max_requests: int, window_seconds: int
    ) -> RateLimitResult:
        """
        Record a request attempt and return whether the caller is rate-limited.

        Returns a ``RateLimitResult`` that contains the limit, remaining
        quota and, when blocked, the number of seconds after which the
        client may retry.
        """
        now = time.monotonic()
        window_start = now - window_seconds

        with self._lock:
            timestamps = self._requests[key]

            # Evict expired entries
            while timestamps and timestamps[0] <= window_start:
                timestamps.popleft()

            if len(timestamps) >= max_requests:
                retry_after = int(timestamps[0] - window_start) + 1
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

    def cleanup(self, max_age_seconds: float = 300.0) -> int:
        """
        Remove keys whose newest entry is older than *max_age_seconds*.

        Returns the number of keys removed.
        """
        now = time.monotonic()
        with self._lock:
            expired_keys = [
                key
                for key, timestamps in self._requests.items()
                if not timestamps or timestamps[-1] < now - max_age_seconds
            ]
            for key in expired_keys:
                del self._requests[key]
            return len(expired_keys)

    def reset(self) -> None:
        """Clear all tracked state. Useful for testing."""
        with self._lock:
            self._requests.clear()
