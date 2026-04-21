"""In-memory per-email login lockout gateway.

Pairs with the rate limiter but keys on the *identity* being attacked (email),
not the *connection* making the attempts (IP).  This is what defends against
brute force; the rate limiter is a pure volume cap.

State is process-local and not persisted.  For a multi-replica deployment
swap this for a Redis-backed implementation behind the same Protocol.
"""

from __future__ import annotations

import math
import threading
import time
from dataclasses import dataclass

from identity_access_management_context.application.gateways import (
    LoginLockoutGateway,
)


@dataclass
class _LockoutEntry:
    consecutive_failed_logins: int = 0
    lockout_until: float | None = None  # time.monotonic() value
    last_touched: float = 0.0


def _normalize_email(email: str) -> str:
    return email.strip().lower()


class InMemoryLoginLockoutGateway(LoginLockoutGateway):
    """Thread-safe per-email failure counter with automatic lockout."""

    def __init__(self, max_failures: int, lockout_seconds: int) -> None:
        if max_failures < 1:
            raise ValueError("max_failures must be >= 1")
        if lockout_seconds < 1:
            raise ValueError("lockout_seconds must be >= 1")
        self._max_failures = max_failures
        self._lockout_seconds = lockout_seconds
        self._entries: dict[str, _LockoutEntry] = {}
        self._lock = threading.Lock()

    def is_locked(self, email: str) -> int | None:
        """Return the remaining lockout seconds if active, else None."""
        key = _normalize_email(email)
        now = time.monotonic()
        with self._lock:
            entry = self._entries.get(key)
            if entry is None or entry.lockout_until is None:
                return None
            remaining = entry.lockout_until - now
            if remaining <= 0:
                entry.lockout_until = None
                return None
            return math.ceil(remaining)

    def record_failed_login(self, email: str) -> None:
        key = _normalize_email(email)
        now = time.monotonic()
        with self._lock:
            entry = self._entries.setdefault(key, _LockoutEntry())
            entry.last_touched = now

            if entry.lockout_until is not None and entry.lockout_until <= now:
                entry.lockout_until = None
                entry.consecutive_failed_logins = 0

            entry.consecutive_failed_logins += 1
            if entry.consecutive_failed_logins >= self._max_failures:
                entry.lockout_until = now + self._lockout_seconds
                entry.consecutive_failed_logins = 0

    def record_successful_login(self, email: str) -> None:
        key = _normalize_email(email)
        with self._lock:
            self._entries.pop(key, None)

    # ── Maintenance / testing helpers ─────────────────────────────

    def cleanup(self, max_age_seconds: float = 3600.0) -> int:
        """Evict entries that haven't been touched in ``max_age_seconds``.

        Entries with an active lockout are kept regardless of age.
        Returns the number of entries removed.
        """
        now = time.monotonic()
        with self._lock:
            stale: list[str] = []
            for key, entry in self._entries.items():
                is_locked_now = entry.lockout_until is not None and entry.lockout_until > now
                if is_locked_now:
                    continue
                if now - entry.last_touched > max_age_seconds:
                    stale.append(key)
            for key in stale:
                del self._entries[key]
            return len(stale)

    def reset(self) -> None:
        """Clear all state. Testing helper."""
        with self._lock:
            self._entries.clear()
