from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class LockoutStatus:
    """Active lockout; ``retry_after_seconds`` is the ceiling-rounded remaining
    window and is always ``>= 1``. Not-locked is signaled as ``None``."""

    retry_after_seconds: int

    def __post_init__(self) -> None:
        if self.retry_after_seconds < 1:
            raise ValueError(f"LockoutStatus.retry_after_seconds must be >= 1; got {self.retry_after_seconds}")


class LoginLockoutGateway(Protocol):
    """Tracks per-email login failure state and serves lockout decisions.

    The use case consults :meth:`is_locked` before verifying credentials and
    drives the counter via :meth:`record_failed_login` / :meth:`record_successful_login`.
    Method names are chosen for business intent (per ``gateway_implementation.prompt.md``)
    rather than CRUD: the rest of the system does not manipulate counters directly.

    Time is passed in by the caller (typically via the shared-kernel ``TimeGateway``)
    so this gateway never reads the clock itself — implementations stay trivially
    testable without monkeypatching.
    """

    def is_locked(self, email: str, now: datetime) -> LockoutStatus | None:
        """Return a LockoutStatus if the account is currently locked, else None."""
        ...

    def record_failed_login(self, email: str, now: datetime) -> None:
        """Account for a failed login attempt against this email."""
        ...

    def record_successful_login(self, email: str) -> None:
        """Clear failure / lockout state for this email after a confirmed successful login."""
        ...
