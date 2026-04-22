from typing import Protocol


class LoginLockoutGateway(Protocol):
    """Tracks per-email login failure state and serves lockout decisions.

    The use case consults :meth:`is_locked` before verifying credentials and
    drives the counter via :meth:`record_failed_login` / :meth:`record_successful_login`.
    Method names are chosen for business intent (per ``gateway_implementation.prompt.md``)
    rather than CRUD: the rest of the system does not manipulate counters directly.
    """

    def is_locked(self, email: str) -> int | None:
        """Return remaining lockout seconds if the account is currently locked, else None."""
        ...

    def record_failed_login(self, email: str) -> None:
        """Account for a failed login attempt against this email."""
        ...

    def record_successful_login(self, email: str) -> None:
        """Clear failure / lockout state for this email after a confirmed successful login."""
        ...
