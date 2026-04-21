"""In-memory per-email login lockout.

Pairs with the rate limiter but lives on a different key — the *identity*
being attacked (email), not the *connection* making the attempts (IP).  This
is what defends against brute force; the rate limiter is a pure volume cap.

State is process-local and not persisted.  See docs/superpowers/specs/
2026-04-21-rate-limiter-design.md §3.1 for the persistence tradeoff.
"""

from __future__ import annotations

import math
import threading
import time
from dataclasses import dataclass


@dataclass
class _LockoutEntry:
    consecutive_failed_logins: int = 0
    lockout_until: float | None = None  # time.monotonic() value
    last_touched: float = 0.0


def _normalize_email(email: str) -> str:
    return email.strip().lower()


class InMemoryLoginLockout:
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

    def is_locked(self, email: str) -> tuple[bool, int]:
        """Return ``(locked, retry_after_seconds)`` for this email.

        ``retry_after_seconds`` is the integer ceiling of remaining lockout
        time; 0 when not locked.
        """
        key = _normalize_email(email)
        now = time.monotonic()
        with self._lock:
            entry = self._entries.get(key)
            if entry is None or entry.lockout_until is None:
                return False, 0
            remaining = entry.lockout_until - now
            if remaining <= 0:
                entry.lockout_until = None
                return False, 0
            return True, math.ceil(remaining)

    def record_failure(self, email: str) -> None:
        """Record one failed login attempt; lock the account if threshold reached."""
        key = _normalize_email(email)
        now = time.monotonic()
        with self._lock:
            entry = self._entries.setdefault(key, _LockoutEntry())
            entry.last_touched = now

            # If a previous lockout has expired, clear it so a fresh sequence can run.
            if entry.lockout_until is not None and entry.lockout_until <= now:
                entry.lockout_until = None
                entry.consecutive_failed_logins = 0

            entry.consecutive_failed_logins += 1
            if entry.consecutive_failed_logins >= self._max_failures:
                entry.lockout_until = now + self._lockout_seconds
                entry.consecutive_failed_logins = 0

    def record_success(self, email: str) -> None:
        """Clear all lockout state for this email."""
        key = _normalize_email(email)
        with self._lock:
            self._entries.pop(key, None)

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
