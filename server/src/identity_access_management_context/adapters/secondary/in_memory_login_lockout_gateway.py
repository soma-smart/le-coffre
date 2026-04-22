"""In-memory per-email login lockout gateway.

Defends against brute-force against a specific account by counting consecutive
failed logins; after a threshold, the account is locked for a fixed duration.
State is process-local and not persisted.

The current time is passed in by the caller (from the shared-kernel
``TimeGateway``) rather than read from ``time.monotonic()`` — this keeps the
adapter trivially testable without monkeypatching the clock.
"""

from __future__ import annotations

import math
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta

from identity_access_management_context.application.gateways import (
    LoginLockoutGateway,
)


@dataclass
class _LockoutEntry:
    consecutive_failed_logins: int = 0
    lockout_until: datetime | None = None


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
        self._lockout_duration = timedelta(seconds=lockout_seconds)
        self._entries: dict[str, _LockoutEntry] = {}
        self._lock = threading.Lock()

    def is_locked(self, email: str, now: datetime) -> int | None:
        key = _normalize_email(email)
        with self._lock:
            entry = self._entries.get(key)
            if entry is None or entry.lockout_until is None:
                return None
            remaining = (entry.lockout_until - now).total_seconds()
            if remaining <= 0:
                entry.lockout_until = None
                return None
            return math.ceil(remaining)

    def record_failed_login(self, email: str, now: datetime) -> None:
        key = _normalize_email(email)
        with self._lock:
            entry = self._entries.setdefault(key, _LockoutEntry())

            if entry.lockout_until is not None and entry.lockout_until <= now:
                entry.lockout_until = None
                entry.consecutive_failed_logins = 0

            entry.consecutive_failed_logins += 1
            if entry.consecutive_failed_logins >= self._max_failures:
                entry.lockout_until = now + self._lockout_duration
                entry.consecutive_failed_logins = 0

    def record_successful_login(self, email: str) -> None:
        key = _normalize_email(email)
        with self._lock:
            self._entries.pop(key, None)
