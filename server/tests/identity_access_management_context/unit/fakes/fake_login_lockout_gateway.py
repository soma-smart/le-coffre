from datetime import datetime

from identity_access_management_context.application.gateways import (
    LockoutStatus,
    LoginLockoutGateway,
)


def _normalize_email(email: str) -> str:
    return email.strip().lower()


class FakeLoginLockoutGateway(LoginLockoutGateway):
    """In-memory fake for unit-testing use cases that depend on login lockout.

    Tests precondition a lockout with :meth:`force_lock` rather than driving the
    gateway through repeated failures; call logs let tests assert which branch
    of the use case fired.  ``now`` is accepted to match the Protocol but the
    fake doesn't use it — tests precondition state via the helpers instead.
    """

    def __init__(self) -> None:
        self.failed_login_calls: list[str] = []
        self.successful_login_calls: list[str] = []
        self._locks: dict[str, int] = {}
        self._record_failed_raises: Exception | None = None
        self._record_successful_raises: Exception | None = None

    def is_locked(self, email: str, now: datetime) -> LockoutStatus | None:
        retry_after = self._locks.get(_normalize_email(email))
        if retry_after is None or retry_after <= 0:
            return None
        return LockoutStatus(retry_after_seconds=retry_after)

    def record_failed_login(self, email: str, now: datetime) -> None:
        if self._record_failed_raises is not None:
            raise self._record_failed_raises
        self.failed_login_calls.append(_normalize_email(email))

    def record_successful_login(self, email: str) -> None:
        if self._record_successful_raises is not None:
            raise self._record_successful_raises
        key = _normalize_email(email)
        self.successful_login_calls.append(key)
        self._locks.pop(key, None)

    # ── Test-only helpers ──────────────────────────────────────────

    def force_lock(self, email: str, retry_after: int) -> None:
        """Precondition a lockout; pass ``retry_after=0`` to seed an expired entry."""
        self._locks[_normalize_email(email)] = retry_after

    def release(self, email: str) -> None:
        self._locks.pop(_normalize_email(email), None)

    def make_record_failed_raise(self, exc: Exception) -> None:
        """Simulate a broken lockout-counter write on failed logins.

        The in-memory impl cannot realistically raise, but future SQL/Redis
        backends can — tests exercise the use case's resilience to gateway
        outages here so a network-backed adapter migration cannot silently
        introduce a fail-open brute-force window.
        """
        self._record_failed_raises = exc

    def make_record_successful_raise(self, exc: Exception) -> None:
        """Simulate a broken lockout-counter reset on successful logins."""
        self._record_successful_raises = exc
